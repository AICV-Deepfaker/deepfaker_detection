import logging
import torch
import torch.nn as nn
from wavelet_lib.metrics.base_metrics_class import calculate_metrics_for_train

from .base_detector import AbstractDetector
from wavelet_lib.detectors.registry import DETECTOR
from wavelet_lib.loss import LOSSFUNC
from transformers import AutoProcessor, CLIPModel
from pytorch_wavelets import DWT1DForward, DWT1DInverse, DWTForward

logger = logging.getLogger(__name__)


@DETECTOR.register_module(module_name="clip_wavelet")
class CLIPDetectorWavelet(AbstractDetector):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.backbone = self.build_backbone(config)

        # Strategy C: 백본 마지막 N 레이어 + post_layernorm만 학습 허용 (나머지 frozen)
        n_trainable = config.get('backbone_trainable_layers', 2)
        self._freeze_backbone_except_last_n(n=n_trainable)

        # ─── Branch 1: 1D DWT on CLS token (기존 로직 유지) ───
        self.dwt = DWT1DForward(wave="db6", J=3)
        self.idwt = DWT1DInverse(wave="db6")
        # 1024-dim CLS feature, J=3 DWT → LL 크기: 137
        self.slp = nn.Linear(137, 137)

        # ─── Branch 2: Patch token 공간 주파수 특징 (Strategy B) ───
        # last_hidden_state[:, 1:, :] → (B, 256, 1024) → reshape → (B, 1024, 16, 16)
        # 1×1 conv으로 채널 축소 → global avg pool → 128-dim
        self.patch_proj = nn.Conv2d(1024, 128, kernel_size=1)
        self.patch_pool = nn.AdaptiveAvgPool2d(1)

        # ─── Branch 3: 이미지 HH 고주파 성분 CNN (Strategy A) ───
        # 입력 이미지에 2D DWT 적용 → HH 서브밴드 (B, 3, ~112, ~112)
        # 작은 CNN으로 주파수 특징 추출 → 256-dim
        self.dwt2d = DWTForward(wave='db4', J=1, mode='reflect')
        self.img_freq_cnn = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1),   # (B, 32, ~56, ~56)
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),  # (B, 64, ~28, ~28)
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(4),                                 # (B, 64, 4, 4)
            nn.Flatten(),                                            # (B, 1024)
            nn.Linear(1024, 256),
        )

        # ─── Fusion head: 1024 (CLS-wavelet) + 128 (patch) + 256 (HH) = 1408 ───
        self.head = nn.Sequential(
            nn.Linear(1024 + 128 + 256, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, 2),
        )

        self.loss_func = self.build_loss(config)
        self.prob, self.label = [], []
        self.correct, self.total = 0, 0

    def _freeze_backbone_except_last_n(self, n: int = 2):
        """Strategy C: 백본 전체 freeze → 마지막 n개 encoder 레이어 + post_layernorm만 unfreeze"""
        for param in self.backbone.parameters():
            param.requires_grad = False

        encoder_layers = self.backbone.encoder.layers
        for layer in encoder_layers[-n:]:
            for param in layer.parameters():
                param.requires_grad = True

        if hasattr(self.backbone, 'post_layernorm'):
            for param in self.backbone.post_layernorm.parameters():
                param.requires_grad = True

    def build_backbone(self, config):
        _, backbone = get_clip_visual(model_name="openai/clip-vit-large-patch14")
        return backbone

    def build_loss(self, config):
        loss_name  = config["loss_func"]
        loss_class = LOSSFUNC[loss_name]

        if loss_name == "focal":
            loss_func = loss_class(
                gamma=config.get("focal_gamma", 2.0),
                alpha=config.get("focal_alpha", None),
            )
        elif loss_name == "weighted_cross_entropy":
            loss_func = loss_class(
                weight=config.get("class_weights", None),
            )
        else:
            loss_func = loss_class()

        return loss_func

    def features(self, data_dict: dict):
        """
        Strategy B: pooler_output(CLS) + last_hidden_state 패치 토큰 동시 반환
        Strategy C: 마지막 N 레이어는 gradient 허용 (torch.no_grad() 제거)
        """
        output = self.backbone(data_dict["image"])
        cls_feat = output["pooler_output"]                  # (B, 1024)
        patch_feat = output["last_hidden_state"][:, 1:, :]  # (B, 256, 1024) — CLS 토큰 제외
        return cls_feat, patch_feat

    def classifier(self, cls_feat: torch.Tensor, patch_feat: torch.Tensor, image: torch.Tensor) -> torch.Tensor:
        B = cls_feat.shape[0]

        # ─── Branch 1: 1D DWT on CLS token ───
        yl, yh = self.dwt(cls_feat.unsqueeze(1))  # yl: (B, 1, 137)
        if self.training:
            brightness_scale = torch.empty(yl.shape[0], 1, 1, device=yl.device).uniform_(0.2, 1.5)
            yl = yl * brightness_scale
        yl_new = self.slp(yl)
        cls_wavelet = self.idwt((yl_new, yh)).squeeze(1)   # (B, 1024)

        # ─── Branch 2: Patch token 공간 특징 (Strategy B) ───
        patch_map = patch_feat.permute(0, 2, 1).reshape(B, 1024, 16, 16)
        patch_proj = self.patch_proj(patch_map)               # (B, 128, 16, 16)
        patch_global = self.patch_pool(patch_proj).flatten(1) # (B, 128)

        # ─── Branch 3: 이미지 HH 고주파 성분 (Strategy A) ───
        _, yh_img = self.dwt2d(image)
        hh_img = yh_img[0][:, :, 2, :, :]         # HH 서브밴드 (B, 3, H', W')
        img_freq_feat = self.img_freq_cnn(hh_img)  # (B, 256)

        # ─── Fusion ───
        combined = torch.cat([cls_wavelet, patch_global, img_freq_feat], dim=1)  # (B, 1408)
        return self.head(combined)

    def get_losses(self, data_dict: dict, pred_dict: dict) -> dict:
        label = data_dict["label"]
        pred = pred_dict["cls"]
        loss = self.loss_func(pred, label)
        loss_dict = {"overall": loss}
        return loss_dict

    def get_train_metrics(self, data_dict: dict, pred_dict: dict) -> dict:
        label = data_dict["label"]
        pred = pred_dict["cls"]
        auc, eer, acc, ap = calculate_metrics_for_train(label.detach(), pred.detach())
        metric_batch_dict = {"acc": acc, "auc": auc, "eer": eer, "ap": ap}
        return metric_batch_dict

    def forward(self, data_dict: dict, inference=False) -> dict:
        image = data_dict["image"]
        cls_feat, patch_feat = self.features(data_dict)
        pred = self.classifier(cls_feat, patch_feat, image)
        prob = torch.softmax(pred, dim=1)[:, 1]
        pred_dict = {"cls": pred, "prob": prob, "feat": cls_feat}
        if inference:
            self.prob.append(pred_dict["prob"].detach().squeeze().cpu().numpy())
            self.label.append(data_dict["label"].detach().squeeze().cpu().numpy())
            _, prediction_class = torch.max(pred, 1)
            correct = (prediction_class == data_dict["label"]).sum().item()
            self.correct += correct
            self.total += data_dict["label"].size(0)
        return pred_dict


def get_clip_visual(model_name="openai/clip-vit-large-patch14"):
    processor = AutoProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)
    return processor, model.vision_model

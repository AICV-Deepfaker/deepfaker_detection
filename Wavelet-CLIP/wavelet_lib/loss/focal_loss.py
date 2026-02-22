import torch
import torch.nn as nn
import torch.nn.functional as F
from .abstract_loss_func import AbstractLossClass
from wavelet_lib.loss.registry import LOSSFUNC


@LOSSFUNC.register_module(module_name="focal")
class FocalLoss(AbstractLossClass):
    """
    Focal Loss — 쉬운 샘플(Real)의 가중치를 낮추고 어려운 샘플(GAN Fake)에 집중.
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Args:
        gamma (float): focusing parameter. gamma=0이면 standard CE와 동일.
                       gamma=2.0 이 일반적. 클수록 hard example에 더 집중.
        alpha (list):  클래스별 가중치 [real_weight, fake_weight].
                       None이면 균등 가중치.
        reduction (str): 'mean' or 'sum'
    """
    def __init__(self, gamma=2.0, alpha=None, reduction='mean'):
        super().__init__()
        self.gamma     = gamma
        self.reduction = reduction

        if alpha is not None:
            self.alpha = torch.tensor(alpha, dtype=torch.float)
        else:
            self.alpha = None

    def forward(self, inputs, targets):
        """
        Args:
            inputs:  (B, num_classes) — raw logits
            targets: (B,)             — class indices (0=real, 1=fake)
        """
        if self.alpha is not None:
            alpha = self.alpha.to(inputs.device)
        else:
            alpha = None

        log_softmax = F.log_softmax(inputs, dim=1)
        softmax     = torch.exp(log_softmax)

        log_pt = log_softmax.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt     = softmax.gather(1, targets.unsqueeze(1)).squeeze(1)

        focal_weight = (1.0 - pt) ** self.gamma

        if alpha is not None:
            at = alpha.gather(0, targets)
            focal_weight = at * focal_weight

        loss = -focal_weight * log_pt

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        return loss


@LOSSFUNC.register_module(module_name="weighted_cross_entropy")
class WeightedCrossEntropyLoss(AbstractLossClass):
    """
    클래스별 가중치가 있는 Cross Entropy Loss.
    Fake 클래스 가중치를 높여 GAN fake 오분류에 더 큰 패널티를 부여.

    Args:
        weight (list): [real_weight, fake_weight]. e.g. [1.0, 8.0]
    """
    def __init__(self, weight=None):
        super().__init__()
        if weight is not None:
            w = torch.tensor(weight, dtype=torch.float)
        else:
            w = None
        self.loss_fn = nn.CrossEntropyLoss(weight=w)

    def forward(self, inputs, targets):
        if self.loss_fn.weight is not None:
            self.loss_fn.weight = self.loss_fn.weight.to(inputs.device)
        return self.loss_fn(inputs, targets)

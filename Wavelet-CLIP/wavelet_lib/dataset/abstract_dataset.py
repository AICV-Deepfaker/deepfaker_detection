# author: Zhiyuan Yan
# email: zhiyuanyan@link.cuhk.edu.cn
# date: 2023-03-30
# description: Abstract Base Class for all types of deepfake datasets.

import sys
import lmdb

sys.path.append('.')

import os
import json

import numpy as np
from copy import deepcopy
import cv2
import random
from PIL import Image

import torch
from torch.utils import data
from torchvision import transforms as T

import albumentations as A

from .albu import IsotropicResize

FFpp_pool=['FaceForensics++','FaceShifter','DeepFakeDetection','FF-DF','FF-F2F','FF-FS','FF-NT']#

def all_in_pool(inputs,pool):
    for each in inputs:
        if each not in pool:
            return False
    return True


class DeepfakeAbstractBaseDataset(data.Dataset):
    """
    Abstract base class for all deepfake datasets.
    """
    def __init__(self, config=None, mode='train'):
        """Initializes the dataset object.

        Args:
            config (dict): A dictionary containing configuration parameters.
            mode (str): A string indicating the mode (train or test).

        Raises:
            NotImplementedError: If mode is not train or test.
        """

        # Set the configuration and mode
        self.config = config
        self.mode = mode
        self.compression = config['compression']
        self.frame_num = config['frame_num'][mode]

        # Check if 'video_mode' exists in config, otherwise set video_level to False
        self.video_level = config.get('video_mode', False)
        self.clip_size = config.get('clip_size', None)
        self.lmdb = config.get('lmdb', False)
        # Dataset dictionary
        self.image_list = []
        self.label_list = []

        # Set the dataset dictionary based on the mode
        if mode == 'train':
            dataset_list = config['train_dataset']
            # Training data should be collected together for training
            image_list, label_list = [], []
            for one_data in dataset_list:
                tmp_image, tmp_label, tmp_name = self.collect_img_and_label_for_one_dataset(one_data)
                image_list.extend(tmp_image)
                label_list.extend(tmp_label)
            if self.lmdb:
                if len(dataset_list)>1:
                    if all_in_pool(dataset_list,FFpp_pool):
                        lmdb_path = os.path.join(config['lmdb_dir'], f"FaceForensics++_lmdb")
                        self.env = lmdb.open(lmdb_path, create=False, subdir=True, readonly=True, lock=False)
                    else:
                        raise ValueError('Training with multiple dataset and lmdb is not implemented yet.')
                else:
                    lmdb_path = os.path.join(config['lmdb_dir'], f"{dataset_list[0] if dataset_list[0] not in FFpp_pool else 'FaceForensics++'}_lmdb")
                    self.env = lmdb.open(lmdb_path, create=False, subdir=True, readonly=True, lock=False)
        elif mode == 'test':
            one_data = config['test_dataset']
            # Test dataset should be evaluated separately. So collect only one dataset each time
            image_list, label_list, name_list = self.collect_img_and_label_for_one_dataset(one_data)
            if self.lmdb:
                lmdb_path = os.path.join(config['lmdb_dir'], f"{one_data}_lmdb" if one_data not in FFpp_pool else 'FaceForensics++_lmdb')
                self.env = lmdb.open(lmdb_path, create=False, subdir=True, readonly=True, lock=False)
        else:
            raise NotImplementedError('Only train and test modes are supported.')

        assert len(image_list)!=0 and len(label_list)!=0, f"Collect nothing for {mode} mode!"
        self.image_list, self.label_list = image_list, label_list

        # Create a dictionary containing the image and label lists
        self.data_dict = {
            'image': self.image_list, 
            'label': self.label_list, 
        }

        print(f"No of {mode} Images: {len(self.image_list)}", flush=True)

        self.transform = self.init_data_aug_method()

    def init_data_aug_method(self):
        dest_transforms = []
        cfg = self.config['data_aug']

        # 1. 기하학적 변형 (구조적 학습용)
        dest_transforms.append(A.HorizontalFlip(p=cfg.get('flip_prob', 0.5)))
        dest_transforms.append(A.Rotate(limit=cfg.get('rotate_limit', 10), p=cfg.get('rotate_prob', 0.5)))

        # 2. Strategy D: 주파수 robustness augmentation
        dest_transforms.append(A.ImageCompression(quality_lower=60, quality_upper=100, p=0.3))
        dest_transforms.append(A.GaussianBlur(blur_limit=(3, 7), p=0.2))
        dest_transforms.append(A.GaussNoise(var_limit=(5.0, 25.0), p=0.2))

        # 3. IsotropicResize (해상도 유지)
        if not self.config.get('with_landmark', False):
            dest_transforms.append(
                IsotropicResize(
                    max_side=self.config['resolution'],
                    interpolation_down=cv2.INTER_AREA,
                    interpolation_up=cv2.INTER_CUBIC,
                    p=1.0
                )
            )

        trans = A.Compose(
            dest_transforms,
            keypoint_params=A.KeypointParams(format='xy') if self.config.get('with_landmark', False) else None
        )
        return trans

    def rescale_landmarks(self, landmarks, original_size=256, new_size=224):
        scale_factor = new_size / original_size
        rescaled_landmarks = landmarks * scale_factor
        return rescaled_landmarks

    def collect_img_and_label_for_one_dataset(self, dataset_name: str):
        """
        JSON 기반으로 frame-level 데이터 로드
        (Celeb-DF-v2, image/frame 기반 전용)
        """

        import os
        import json
        import random

        label_list = []
        frame_path_list = []
        video_name_list = []

        json_path = "/content/Wavelet-CLIP/preprocessing/dataset_json/GAN_DIFFUSION.json"

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Dataset JSON not found: {json_path}")

        with open(json_path, "r") as f:
            dataset_info = json.load(f)

        # ✔ 구조: dataset → label → split → video_id
        dataset_info = dataset_info[dataset_name]

        mode = self.mode  # "train" or "test"

        for label_name in ["real", "fake"]:
            if label_name not in dataset_info:
                continue

            if mode not in dataset_info[label_name]:
                continue

            label = self.config['label_dict'][label_name]

            for video_id, video_info in dataset_info[label_name][mode].items():
                frames = video_info["frames"]

                def safe_sort_key(path):
                    name = os.path.splitext(os.path.basename(path))[0]
                    try:
                        return int(name)
                    except ValueError:
                        # 숫자 추출 fallback (img_000123 → 123)
                        digits = "".join(filter(str.isdigit, name))
                        return int(digits) if digits else 0

                frames = sorted(frames, key=safe_sort_key)

                # frame_num 적용
                total_frames = len(frames)
                if self.frame_num is not None and total_frames > self.frame_num:
                    if self.video_level:
                        start = random.randint(0, total_frames - self.frame_num)
                        frames = frames[start:start + self.frame_num]
                    else:
                        step = max(total_frames // self.frame_num, 1)
                        frames = frames[::step][:self.frame_num]

                # 저장
                frame_path_list.extend(frames)
                label_list.extend([label] * len(frames))
                video_name_list.extend([video_id] * len(frames))

        # 셔플
        shuffled = list(zip(frame_path_list, label_list, video_name_list))
        random.shuffle(shuffled)
        frame_path_list, label_list, video_name_list = zip(*shuffled)

        return list(frame_path_list), list(label_list), list(video_name_list)


    def load_rgb(self, file_path):
        """
        Load an RGB image from an absolute file path and resize it.

        Args:
            file_path (str): absolute path to image

        Returns:
            PIL.Image
        """
        import os
        import cv2
        import numpy as np
        from PIL import Image

        size = self.config["resolution"]

        # =========================
        # 일반 filesystem 로딩
        # =========================
        if not self.lmdb:
            assert os.path.exists(file_path), f"{file_path} does not exist"

            img = cv2.imread(file_path)
            if img is None:
                raise ValueError(f"Loaded image is None: {file_path}")

        # =========================
        # LMDB 로딩 (선택)
        # =========================
        else:
            with self.env.begin(write=False) as txn:
                image_bin = txn.get(file_path.encode())
                if image_bin is None:
                    raise FileNotFoundError(f"LMDB key not found: {file_path}")

                image_buf = np.frombuffer(image_bin, dtype=np.uint8)
                img = cv2.imdecode(image_buf, cv2.IMREAD_COLOR)

        # =========================
        # 후처리
        # =========================
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_CUBIC)

        return Image.fromarray(img.astype(np.uint8))

    def load_mask(self, file_path):
        """
        Load a binary mask image from a file path and resize it to a specified resolution.

        Args:
            file_path: A string indicating the path to the mask file.

        Returns:
            A numpy array containing the loaded and resized mask.

        Raises:
            None.
        """
        size = self.config['resolution']
        if file_path is None:
            return np.zeros((size, size, 1))
        if not self.lmdb:
            if not file_path[0] == '.':
                file_path =  f'./{self.config["rgb_dir"]}\\'+file_path
            if os.path.exists(file_path):
                mask = cv2.imread(file_path, 0)
                if mask is None:
                    mask = np.zeros((size, size))
            else:
                return np.zeros((size, size, 1))
        else:
            with self.env.begin(write=False) as txn:
                # transfer the path format from rgb-path to lmdb-key
                if file_path[0]=='.':
                    file_path=file_path.replace('./datasets\\','')

                image_bin = txn.get(file_path.encode())
                if image_bin is None:
                    mask = np.zeros((size, size,3))
                else:
                    image_buf = np.frombuffer(image_bin, dtype=np.uint8)
                    # cv2.IMREAD_GRAYSCALE为灰度图，cv2.IMREAD_COLOR为彩色图
                    mask = cv2.imdecode(image_buf, cv2.IMREAD_COLOR)
        mask = cv2.resize(mask, (size, size)) / 255
        mask = np.expand_dims(mask, axis=2)
        return np.float32(mask)

    def load_landmark(self, file_path):
        """
        Load 2D facial landmarks from a file path.

        Args:
            file_path: A string indicating the path to the landmark file.

        Returns:
            A numpy array containing the loaded landmarks.

        Raises:
            None.
        """
        if file_path is None:
            return np.zeros((81, 2))
        if not self.lmdb:
            if not file_path[0] == '.':
                file_path =  f'./{self.config["rgb_dir"]}\\'+file_path
            if os.path.exists(file_path):
                landmark = np.load(file_path)
            else:
                return np.zeros((81, 2))
        else:
            with self.env.begin(write=False) as txn:
                # transfer the path format from rgb-path to lmdb-key
                if file_path[0]=='.':
                    file_path=file_path.replace('./datasets\\','')
                binary = txn.get(file_path.encode())
                landmark = np.frombuffer(binary, dtype=np.uint32).reshape((81, 2))
                landmark=self.rescale_landmarks(np.float32(landmark), original_size=256, new_size=self.config['resolution'])
        return landmark

    def to_tensor(self, img):
        """
        Convert an image to a PyTorch tensor.
        """
        return T.ToTensor()(img)

    def normalize(self, img):
        """
        Normalize an image.
        """
        mean = self.config['mean']
        std = self.config['std']
        normalize = T.Normalize(mean=mean, std=std)
        return normalize(img)

    def data_aug(self, img, landmark=None, mask=None, augmentation_seed=None):
        """
        Apply data augmentation to an image, landmark, and mask with video-level seed.
        """
        import albumentations as A

        # 1. 시드 고정: 비디오 내의 모든 프레임이 동일한 변형을 겪도록 함
        if augmentation_seed is not None:
            random.seed(augmentation_seed)
            np.random.seed(augmentation_seed)
            try:
                A.random_utils.set_seed(augmentation_seed)
            except AttributeError:
                pass

        # 2. 인자 구성
        kwargs = {'image': img}

        if landmark is not None:
            kwargs['keypoints'] = landmark

        if mask is not None:
            if len(mask.shape) == 3 and mask.shape[2] == 1:
                mask = mask.squeeze(2)
            kwargs['mask'] = mask

        # 3. Augmentation 적용
        transformed = self.transform(**kwargs)

        # 4. 결과 추출
        augmented_img = transformed['image']
        augmented_landmark = transformed.get('keypoints')
        augmented_mask = transformed.get('mask')

        if augmented_mask is None:
            augmented_mask = mask

        if augmented_landmark is not None:
            augmented_landmark = np.array(augmented_landmark)

        # 5. 시드 리셋
        if augmentation_seed is not None:
            random.seed()
            np.random.seed()

        return augmented_img, augmented_landmark, augmented_mask

    def __getitem__(self, index, no_norm=False):
        """
        Unified __getitem__ supporting:
        - GAN video frames (frames/)
        - Diffusion image-only data
        - Multiple dataset roots
        """

        import os
        import random
        import numpy as np
        import torch
        from copy import deepcopy

        # =====================================================
        # 0. Helper: resolve path using dataset_roots
        # =====================================================
        def resolve_image_path(rel_path):
            # absolute path -> 그대로 사용
            if os.path.isabs(rel_path):
                return rel_path

            # prefix-based roots (권장 방식)
            for prefix, root in self.config.get("dataset_roots", {}).items():
                if rel_path.startswith(prefix):
                    sub_path = rel_path[len(prefix):].lstrip("/")
                    return os.path.join(root, sub_path)

            # fallback (single root)
            base_root = self.config.get("dataset_root", "")
            return os.path.join(base_root, rel_path) if base_root else rel_path

        # =====================================================
        # 1. index 데이터 가져오기
        # =====================================================
        image_paths = self.data_dict["image"][index]
        label = self.data_dict["label"][index]

        # image-only 대응
        if not isinstance(image_paths, list):
            image_paths = [image_paths]

        image_tensors = []
        landmark_tensors = []
        mask_tensors = []

        augmentation_seed = None

        # =====================================================
        # 2. frame / image loop
        # =====================================================
        for i, rel_image_path in enumerate(image_paths):

            # ---------- 절대경로 resolve ----------
            image_path = resolve_image_path(rel_image_path)

            if not os.path.exists(image_path):
                raise FileNotFoundError(f"[Dataset] Missing image: {image_path}")

            # ---------- augmentation seed (video-level) ----------
            if self.video_level and i == 0:
                augmentation_seed = random.randint(0, 2**32 - 1)

            # ---------- frame 기반 여부 ----------
            is_frame_data = "frames" in image_path

            # ---------- mask / landmark 경로 ----------
            if is_frame_data and self.config.get("with_mask", False):
                mask_path = image_path.replace("frames", "masks")
            else:
                mask_path = None

            if is_frame_data and self.config.get("with_landmark", False):
                landmark_path = (
                    image_path.replace("frames", "landmarks")
                              .replace(".png", ".npy")
                )
            else:
                landmark_path = None

            # =====================================================
            # 3. Load image / mask / landmark
            # =====================================================
            image = self.load_rgb(image_path)
            image = np.array(image)

            # 전처리된 이미지를 resolution 크기로 통일
            image = cv2.resize(image, (self.config['resolution'], self.config['resolution']), interpolation=cv2.INTER_LINEAR)

            landmarks = None

            if mask_path and os.path.exists(mask_path):
                mask = self.load_mask(mask_path)
            else:
                mask = None

            # =====================================================
            # 4. Data Augmentation
            # =====================================================
            if self.mode == "train" and self.config.get("use_data_augmentation", False):
                image_aug, landmarks_aug, mask_aug = self.data_aug(
                    image, landmarks, mask, augmentation_seed
                )
            else:
                image_aug = deepcopy(image)
                landmarks_aug = deepcopy(landmarks)
                mask_aug = deepcopy(mask)

            # =====================================================
            # 5. To tensor
            # =====================================================
            if not no_norm:
                image_tensor = self.normalize(self.to_tensor(image_aug))
            else:
                image_tensor = self.to_tensor(image_aug)

            landmark_tensor = (
                torch.from_numpy(landmarks_aug)
                if landmarks_aug is not None else None
            )
            mask_tensor = (
                torch.from_numpy(mask_aug)
                if mask_aug is not None else None
            )

            image_tensors.append(image_tensor)
            landmark_tensors.append(landmark_tensor)
            mask_tensors.append(mask_tensor)

        # =====================================================
        # 6. video_level / image_level 정리
        # =====================================================
        if self.video_level:
            image_tensors = torch.stack(image_tensors, dim=0)

            landmark_tensors = (
                torch.stack(landmark_tensors, dim=0)
                if all(l is not None for l in landmark_tensors)
                else None
            )
            mask_tensors = (
                torch.stack(mask_tensors, dim=0)
                if all(m is not None for m in mask_tensors)
                else None
            )
        else:
            image_tensors = image_tensors[0]
            landmark_tensors = landmark_tensors[0]
            mask_tensors = mask_tensors[0]

        return image_tensors, label, landmark_tensors, mask_tensors



    @staticmethod
    def collate_fn(batch):
        """
        Collate a batch of data points.

        Args:
            batch (list): A list of tuples containing the image tensor, the label tensor,
                          the landmark tensor, and the mask tensor.

        Returns:
            A tuple containing the image tensor, the label tensor, the landmark tensor,
            and the mask tensor.
        """
        # Separate the image, label, landmark, and mask tensors
        images, labels, landmarks, masks = zip(*batch)

        # 이미지 크기 불일치 해결: 배치 내 모든 이미지를 224×224로 통일
        standard_size = (224, 224)
        processed_images = []
        for img in images:
            if img.shape[1:] != standard_size:
                img = torch.nn.functional.interpolate(
                    img.unsqueeze(0),
                    size=standard_size,
                    mode='bilinear',
                    align_corners=False
                ).squeeze(0)
            processed_images.append(img)

        images = torch.stack(processed_images, dim=0)
        labels = torch.LongTensor(labels)

        # Special case for landmarks and masks if they are None
        if not any(landmark is None or (isinstance(landmark, list) and None in landmark) for landmark in landmarks):
            try:
                landmarks = torch.stack(landmarks, dim=0)
            except RuntimeError:
                landmarks = None
        else:
            landmarks = None

        if not any(m is None or (isinstance(m, list) and None in m) for m in masks):
            try:
                masks = torch.stack(masks, dim=0)
            except RuntimeError:
                masks = None
        else:
            masks = None

        # Create a dictionary of the tensors
        data_dict = {}
        data_dict['image'] = images
        data_dict['label'] = labels
        data_dict['landmark'] = landmarks
        data_dict['mask'] = masks
        return data_dict

    def __len__(self):
        """
        Return the length of the dataset.

        Args:
            None.

        Returns:
            An integer indicating the length of the dataset.

        Raises:
            AssertionError: If the number of images and labels in the dataset are not equal.
        """
        assert len(self.image_list) == len(self.label_list), 'Number of images and labels are not equal'
        return len(self.image_list)

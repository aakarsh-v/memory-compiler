from pathlib import Path
from typing import List, Union
from PIL import Image

from app.core.errors import AppException
from app.ml.base import EmbeddingProvider


class OpenCLIPEmbeddingProvider(EmbeddingProvider):
    """
    Multimodal image-text embedding provider powered by OpenCLIP / PyTorch.
    Embeds both natural-language queries and extracted video frames into a shared vector space.
    """

    def __init__(self, model_id: str = "ViT-B-32", pretrained: str = "laion2b_s34b_b79k", device: str = "cpu"):
        self._model_id = f"{model_id}:{pretrained}"
        self._device = device
        self._dimension = 512

        try:
            import torch
            import open_clip

            self.torch = torch
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                model_id,
                pretrained=pretrained,
                device=device
            )
            self.tokenizer = open_clip.get_tokenizer(model_id)
            self.model.eval()
            self._dimension = self.model.visual.output_dim
        except ImportError:
            raise AppException(
                "OPENCLIP_NOT_INSTALLED",
                "open_clip_torch is not installed in the environment. Run: pip install open_clip_torch",
                status_code=500
            )
        except Exception as e:
            raise AppException(
                "MODEL_LOAD_FAILED",
                f"Failed to load OpenCLIP model {model_id} ({pretrained}): {str(e)}",
                status_code=500
            )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        with self.torch.no_grad():
            tokenized = self.tokenizer(texts).to(self._device)
            text_features = self.model.encode_text(tokenized)
            # L2 normalize
            text_features /= text_features.norm(dim=-1, keepdim=True)
            return text_features.cpu().numpy().tolist()

    def embed_frames(self, frame_sources: List[Union[str, Path, bytes]]) -> List[List[float]]:
        images = []
        for src in frame_sources:
            if isinstance(src, bytes):
                import io
                img = Image.open(io.BytesIO(src)).convert("RGB")
            else:
                img = Image.open(src).convert("RGB")
            images.append(self.preprocess(img))

        with self.torch.no_grad():
            image_tensor = self.torch.stack(images).to(self._device)
            image_features = self.model.encode_image(image_tensor)
            # L2 normalize
            image_features /= image_features.norm(dim=-1, keepdim=True)
            return image_features.cpu().numpy().tolist()

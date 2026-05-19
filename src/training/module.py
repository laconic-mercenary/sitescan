from __future__ import annotations

import lightning as L
import torch
from torchmetrics.classification import BinaryJaccardIndex, BinaryPrecision, BinaryRecall

from src.config.load import LossConfig, TrainingConfig
from src.training.losses import CombinedSegmentationLoss


class SegmentationModule(L.LightningModule):
    def __init__(self, model, training_config: TrainingConfig, loss_config: LossConfig) -> None:
        super().__init__()
        self.model = model
        self.training_config = training_config
        self.loss_fn = CombinedSegmentationLoss(
            bce_weight=loss_config.bce_weight,
            dice_weight=loss_config.dice_weight,
            pos_weight=training_config.pos_weight,
        )
        self.val_iou = BinaryJaccardIndex()
        self.val_precision = BinaryPrecision()
        self.val_recall = BinaryRecall()
        self.save_hyperparameters(
            {
                "learning_rate": training_config.learning_rate,
                "weight_decay": training_config.weight_decay,
                "pos_weight": training_config.pos_weight,
                "bce_weight": loss_config.bce_weight,
                "dice_weight": loss_config.dice_weight,
            }
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.model(inputs)

    def training_step(self, batch, batch_idx: int) -> torch.Tensor:
        images, masks = batch
        logits = self(images)
        loss = self.loss_fn(logits, masks)
        self.log("train/loss", loss, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx: int) -> None:
        images, masks = batch
        logits = self(images)
        loss = self.loss_fn(logits, masks)
        predictions = torch.sigmoid(logits)
        self.val_iou.update(predictions, masks.int())
        self.val_precision.update(predictions, masks.int())
        self.val_recall.update(predictions, masks.int())
        self.log("val/loss", loss, prog_bar=True)

    def on_validation_epoch_end(self) -> None:
        self.log("val/iou", self.val_iou.compute(), prog_bar=True)
        self.log("val/precision", self.val_precision.compute())
        self.log("val/recall", self.val_recall.compute())
        self.val_iou.reset()
        self.val_precision.reset()
        self.val_recall.reset()

    def configure_optimizers(self):
        return torch.optim.AdamW(
            self.parameters(),
            lr=self.training_config.learning_rate,
            weight_decay=self.training_config.weight_decay,
        )

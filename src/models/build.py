from __future__ import annotations

import segmentation_models_pytorch as smp

from src.config.load import ModelConfig


def build_model(config: ModelConfig):
    return smp.Unet(
        encoder_name=config.encoder,
        encoder_weights=config.encoder_weights,
        in_channels=config.in_channels,
        classes=config.num_classes,
        decoder_channels=config.decoder_channels,
        activation=config.activation,
    )

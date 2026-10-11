"""Frozen VoxCPM2 AudioVAE loader.

FreyaTTS generates 64-dim latents at 25 Hz and relies on the pretrained
VoxCPM2 AudioVAE (openbmb/VoxCPM2) to decode them to 48 kHz waveforms.
Uses the minimal vendored VoxCPM AudioVAE implementation.
"""

import os

import torch
from huggingface_hub import hf_hub_download
from src.vendor.freyatts_voxcpm_audiovae import AudioVAE as AudioVAEV2
from src.vendor.freyatts_voxcpm_audiovae import AudioVAEConfig as AudioVAEConfigV2


def load_audio_vae(device="cuda", token=None):
    """Download and return the frozen VoxCPM2 AudioVAE in eval mode on `device`."""
    path = hf_hub_download("openbmb/VoxCPM2", "audiovae.pth", token=token or os.environ.get("HF_TOKEN"))
    vae = AudioVAEV2(AudioVAEConfigV2())

    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    vae.load_state_dict(ckpt.get("state_dict", ckpt), strict=False)

    vae = vae.to(device).float().eval()
    for p in vae.parameters():
        p.requires_grad = False
    return vae

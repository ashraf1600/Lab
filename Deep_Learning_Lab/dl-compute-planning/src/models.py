"""Two CNN workloads of very different size, so the hardware comparison has both a light and a heavy case."""
import torch.nn as nn


def conv_block(c_in, c_out):
    return nn.Sequential(nn.Conv2d(c_in, c_out, 3, padding=1), nn.BatchNorm2d(c_out), nn.ReLU(), nn.MaxPool2d(2))


class SmallCNN(nn.Module):
    """Light workload: 1x28x28 images (MNIST-sized), about 0.1 M parameters."""

    def __init__(self, num_classes=10):
        super().__init__()
        self.net = nn.Sequential(conv_block(1, 16), conv_block(16, 32), nn.Flatten(),
                                 nn.Linear(32 * 7 * 7, 64), nn.ReLU(), nn.Linear(64, num_classes))

    def forward(self, x):
        return self.net(x)


class MediumCNN(nn.Module):
    """Heavy workload: 3x64x64 colour images, four conv blocks, about 0.24 M parameters but far more FLOPs."""

    def __init__(self, num_classes=10):
        super().__init__()
        self.net = nn.Sequential(conv_block(3, 32), conv_block(32, 64), conv_block(64, 128), conv_block(128, 128),
                                 nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(128, num_classes))

    def forward(self, x):
        return self.net(x)


WORKLOADS = {  # name: (model class, input shape of one sample)
    "small_cnn": (SmallCNN, (1, 28, 28)),
    "medium_cnn": (MediumCNN, (3, 64, 64)),
}


def count_parameters(model):
    return sum(p.numel() for p in model.parameters())

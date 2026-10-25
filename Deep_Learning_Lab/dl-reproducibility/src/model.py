"""Small CNN for 8x8 single-channel digit images."""
import torch.nn as nn


class DigitsCNN(nn.Module):
    def __init__(self, num_classes: int = 10, dropout: float = 0.25):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),   # (1, 8, 8)  -> (16, 8, 8)
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),  # (16, 8, 8) -> (32, 8, 8)
            nn.ReLU(),
            nn.MaxPool2d(2),                              # -> (32, 4, 4)
            nn.Dropout(dropout),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),                                 # 32 * 4 * 4 = 512
            nn.Linear(32 * 4 * 4, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

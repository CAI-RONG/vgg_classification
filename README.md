# vgg_classification


VGG16屬於比較多層的網路，會容易有梯度消失 (Vanishing gradient) 的問題出現，可以利用Batch normalize來改善
因此實作上在每一層增加 Batch normalize，減緩梯度消失並加速收斂

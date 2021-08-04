# -*- coding: utf-8 -*-
"""vgg16_v3 (2).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1B25EZGe3c_AEoRg1Xedu_sMhR9VZ8Bz3
"""

# -*- coding: utf-8 -*-
from torch.utils.tensorboard import SummaryWriter
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
import numpy as np
import torch.optim as optim
from sklearn.metrics import f1_score


BATCH_SIZE = 16
EPOCHS = 20
LR = 0.002
#PATH_OF_DATA = '/content/gdrive/MyDrive/data/bangla_banknote_v2'
PATH_OF_DATA = './data/bangla_banknote_v2'

# GPU
device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
print('GPU state:', device)

# default `log_dir` is "runs" - we'll be more specific here
writer = SummaryWriter(PATH_OF_DATA + '/Image_Training')

transform = transforms.Compose([transforms.Resize((224, 224)),
                                transforms.ToTensor(),
                                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

origset = torchvision.datasets.ImageFolder(
    PATH_OF_DATA + '/Training', transform=transform)
n_origset = len(origset)  # total number of examples
n_test = int(0.5 * n_origset)  # take 50% for test

trainset, testset = torch.utils.data.random_split(
    dataset=origset, lengths=[n_origset - n_test, n_test])

trainloader = torch.utils.data.DataLoader(
    trainset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
testloader = torch.utils.data.DataLoader(
    testset, batch_size=BATCH_SIZE, shuffle=False, drop_last=True)

classes = (1, 10, 100, 1000, 2, 20, 5, 50, 500)
num_classes = len(classes)

# 顯示圖像的function
def imshow(img):
    img = img / 2 + 0.5
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.show()

# 取得圖片與標記資料
dataiter = iter(trainloader)
images, labels = dataiter.next()

for j in range(BATCH_SIZE):
    # print label
    print("This label is a "+str(classes[labels[j]]))
    # show images
    imshow(images[j])

### model ###
def conv_layer(chann_in, chann_out):
    layer = nn.Sequential(
        nn.Conv2d(chann_in, chann_out, 3, padding='same'),
        nn.BatchNorm2d(chann_out),
        nn.ReLU()
    )
    return layer


def conv_block(in_list, out_list):
    layers = [conv_layer(in_list[i], out_list[i])
              for i in range(len(in_list))]
    layers += [nn.MaxPool2d(2, stride=2)]
    return nn.Sequential(*layers)


def fc_layer(size_in, size_out):
    layer = nn.Sequential(
        nn.Linear(size_in, size_out),
        nn.BatchNorm1d(size_out),
        nn.ReLU()
    )
    return layer


class VGG16(nn.Module):
    def __init__(self, n_classes=num_classes):
        super(VGG16, self).__init__()
        self.layer1 = conv_block([3, 64], [64, 64])
        self.layer2 = conv_block([64, 128], [128, 128])
        self.layer3 = conv_block([128, 256, 256], [256, 256, 256])
        self.layer4 = conv_block([256, 512, 512], [512, 512, 512])
        self.layer5 = conv_block([512, 512, 512], [512, 512, 512])

        self.classifier = nn.Sequential(
            fc_layer(512*7*7, 4096),
            fc_layer(4096, 4096),
            nn.Linear(4096, n_classes),
        )

    def forward(self, x):
        x = self.layer1(x)  # (3*224*224) -> (64*112*112)
        x = self.layer2(x)  # (64*112*112) -> (128*56*56)
        x = self.layer3(x)  # (128*56*56) -> (256*28*28)
        x = self.layer4(x)  # (256*28*28) -> (512*14*14)
        x = self.layer5(x)  # (512*14*14) -> (512*7*7) # (BATCH_SIZE*512*7*7)
        x = x.view(x.size(0), -1)  # (BATCH_SIZE, 25088)  512*7*7 = 25088
        out = self.classifier(x)
        return out


net = VGG16().to(device)
print(net)

# tensorboard
writer.add_graph(net, images.to(device))
writer.close()

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), momentum=0.9, lr=LR)

for epoch in range(EPOCHS):
    running_loss = 0.0
    for i, data in enumerate(trainloader, 0):

        # 取得訓練資料
        inputs, labels = data
        inputs, labels = inputs.to(device), labels.to(device)

        # 將gradients parameter歸零
        optimizer.zero_grad()

        # forward + backward + 最佳化(Optimization)
        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        # print statistics
        running_loss += loss.item()    # 把全部的less加起來，等等會再除
        mini_batch_size = 10       # 每mini_patch_size次就進行測試

        if i % mini_batch_size == mini_batch_size-1:
            print('[%d, %5d] loss: %.3f' %
                  (epoch + 1, i + 1, running_loss / mini_batch_size))
            class_correct = list(0. for i in range(10))
            class_total = list(0. for i in range(10))

            validation = torch.utils.data.DataLoader(
                testset, batch_size=BATCH_SIZE, shuffle=False, drop_last=True)

            writer.add_scalar('validation loss', running_loss /
                              mini_batch_size, epoch * len(validation) + i)

            actuals = []
            predications = []
            running_loss = 0.0     # 歸零，不然還會累加

            with torch.no_grad():

                for data in validation:
                    images, labels = data
                    images, labels = images.to(device), labels.to(device)
                    outputs = net(images)

                    predication = outputs.argmax(dim=1, keepdim=True)
                    actuals.extend(labels.view_as(predication))
                    predications.extend(predication)

                    _, predicted = torch.max(outputs, 1)
                    c = (predicted == labels).squeeze()

                    for i in range(BATCH_SIZE):
                        # imshow(images[i].cpu())
                        label = labels[i]
                        # Tensor.item() → number
                        class_correct[label] += c[i].item()
                        class_total[label] += 1

                for i in range(9):
                    print('Accuracy of %5s : %2d %%' %
                          (classes[i], 100 * class_correct[i] / class_total[i]))

                print('Accuracy of All : %2d %%' %
                      (100 * sum(class_correct) / sum(class_total)))
                writer.add_scalar('Accuracy', (100 * sum(class_correct) /
                                  sum(class_total)), epoch * len(validation) + i)

                print("----------------------------------------")


PATH = PATH_OF_DATA + '/Image_Training.pth'
torch.save(net.state_dict(), PATH)
print('Finished Training')

# Commented out IPython magic to ensure Python compatibility.
# %reload_ext tensorboard

# Commented out IPython magic to ensure Python compatibility.
# %tensorboard --logdir='/content/gdrive/MyDrive/data/bangla_banknote_v2/Image_Training' --port=6007

# 測試資料 testloader
total_correct = 0
total_images = 0
confusion_matrix = np.zeros([9, 9], int)
with torch.no_grad():
    for data in testloader:
        images, labels = data
        images, labels = images.to(device), labels.to(device)
        outputs = net(images)
        _, predicted = torch.max(outputs.data, 1)
        total_images += labels.size(0)
        total_correct += (predicted == labels).sum().item()
        for i, l in enumerate(labels):
            confusion_matrix[l.item(), predicted[i].item()] += 1

model_accuracy = total_correct / total_images * 100
print('Model accuracy on {0} test images: {1:.2f}%'.format(
    total_images, model_accuracy))
print("\n")
print('{0:10s} - {1}'.format('Category', 'Accuracy'))
# print("size: ", len(confusion_matrix))
for i, r in enumerate(confusion_matrix):
    # print("i, r: ", i,r)
    print('{0:10d} - {1:.1f}'.format(classes[i], r[i]/np.sum(r)*100))


fig, ax = plt.subplots(1, 1, figsize=(8, 6))
ax.matshow(confusion_matrix, aspect='auto', vmin=0,
           vmax=1000, cmap=plt.get_cmap('Blues'))
plt.ylabel('Actual Category')
plt.yticks(range(10), classes)
plt.xlabel('Predicted Category')
plt.xticks(range(10), classes)
plt.show()

# Simple-NumPy-ML

This is my testground for the basics of machine learning. The implementation is in Python 3 and only NumPy is required (see `./requirements.txt`). *You **DO NOT** need a GPU to train your model.* This project is inspired by a collection of resources that I found useful on the Internet:

* Michael Nielsen's [Neural Networks and Deep Learning](http://neuralnetworksanddeeplearning.com/)
* Yani Ioannou's blog posts for deriving [single-layer backpropagation](https://blog.yani.ai/deltarule/) and [multi-layer backpropagation](https://blog.yani.ai/backpropagation/)
* Sargur N. Srihari's [course on deep learning](https://cedar.buffalo.edu/~srihari/CSE676/) has a nice derivation of matrix/jacobian based backpropagation, [course note](https://cedar.buffalo.edu/~srihari/CSE676/6.5.2%20Chain%20Rule.pdf) (a copy of it can be found in ./misc/6.5.2 Chain Rule.pdf)
* Pavithra Solai's article [Convolutions and Backpropagations](https://pavisj.medium.com/convolutions-and-backpropagations-46026a8f5d2c) is easy to understand for cases without stride
* Mayank Kaushik's article [Backpropagation for Convolution with Strides](https://medium.com/@mayank.utexas/backpropagation-for-convolution-with-strides-8137e4fc2710) and its [Part 2](https://medium.com/@mayank.utexas/backpropagation-for-convolution-with-strides-fb2f2efc4faa) are well written for general cases (with stride)
* Rae's video explanation [Episode 6 - Convolution Layer Backpropagation - Convolutional Neural Network from Scratch](https://www.youtube.com/watch?v=njlyOAiK_yE) has nice animations for understanding the topic
* S. Do.'s article [Vectorized convolution operation using NumPy](https://medium.com/latinxinai/vectorized-convolution-operation-using-numpy-b122fd52fba3) explains how to use Einstein summation convention for convolution perfectly
* Vincent Dumoulin and Francesco Visin's [A guide to convolution arithmetic for deep learning](https://arxiv.org/abs/1603.07285)
* Jason Brownlee's [A Gentle Introduction to Dropout for Regularizing Deep Neural Networks](https://machinelearningmastery.com/dropout-for-regularizing-deep-neural-networks/) is an informative overview of dropout with lots of references
* [This excellent answer](https://datascience.stackexchange.com/questions/117082/how-can-i-implement-dropout-in-scikit-learn/117083#117083) by Conner explains the practical aspect of dropout clearly

## Some Notes

* I do not care the execution speed of the constructed model as the main purpose of this project is for me to understand the basics in the field. It is slow, but can still get the job done in a reasonable amount of time (for small networks).
* Currently convolution/correlation is implemented in the naive way (sliding a kernel across the matrix). Ideally, both the feedforward and backpropagation pass of convolutional layer can be implemented as matrix multiplications.

## Datasets

### MNIST

The MNIST dataset for training and evaluation of handwritten digits are obtained from [Yann LeCun's MNIST page](http://yann.lecun.com/exdb/mnist/). This dataset is included in `./dataset/mnist/`.

### Fashion-MNIST

### CIFAR-10

### CIFAR-100

## Additional Dependencies (optional)

As mentioned earlier, the only required third-party library is NumPy. Additional libraries can be installed to support more functionalities (see `./requirements_extra.txt`). To install all dependencies in one go, pick the requirement files of your choice and execute (using two files as an example)

```Shell
pip install -r requirements.txt -r requirements_extra.txt
```

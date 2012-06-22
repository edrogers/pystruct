import numpy as np
import matplotlib.pyplot as plt

from scipy import sparse
from pyqpbo import alpha_expansion_graph

#from crf import MultinomialFixedGraphCRFNoBias
from crf import MultinomialFixedGraphCRFNoBias
#from crf import MultinomialGridCRF
#from structured_perceptron import StructuredPerceptron
from structured_svm import StructuredSVM
#SubgradientStructuredSVM
#from examples_latent_crf import make_dataset_easy_latent
from examples_latent_crf import make_dataset_easy_latent_explicit


from IPython.core.debugger import Tracer
tracer = Tracer()


def make_dataset_blocks_multinomial(n_samples=20):
    Y = np.zeros((n_samples, 10, 12, 3))
    Y[:, :, :4, 0] = -1
    Y[:, :, 4:8, 1] = -1
    Y[:, :, 8:16, 2] = -1
    X = Y + 0.5 * np.random.normal(size=Y.shape)
    Y = np.argmin(Y, axis=3).astype(np.int32)
    return X, Y


def make_dataset_checker_multinomial():
    Y = np.ones((20, 10, 12, 3))
    Y[:, ::2, ::2, 0] = -1
    Y[:, 1::2, 1::2, 1] = -1
    Y[:, :, :, 2] = 0
    X = Y + 1.5 * np.random.normal(size=Y.shape)
    Y = np.argmin(Y, axis=3).astype(np.int32)
    return X, Y


def make_dataset_big_checker():
    y_small = np.ones((11, 13), dtype=np.int32)
    y_small[::2, ::2] = 0
    y_small[1::2, 1::2] = 0
    y = y_small.repeat(3, axis=0).repeat(3, axis=1)
    Y = np.repeat(y[np.newaxis, :, :], 20, axis=0)
    X = Y + 0.5 * np.random.normal(size=Y.shape)
    Y = (Y > 0).astype(np.int32)
    # make unaries with 4 pseudo-classes
    X = np.r_['-1, 4,0', X, -X].copy("C")
    return X, Y


def make_dataset_big_checker_extended():
    y_small = np.zeros((6, 6), dtype=np.int32)
    y_small[::2, ::2] = 2
    y_small[1::2, 1::2] = 2
    y = y_small.repeat(3, axis=0).repeat(3, axis=1)
    y[1::3, 1::3] = 1
    y[1::6, 1::6] = 3
    y[4::6, 4::6] = 3
    Y = np.repeat(y[np.newaxis, :, :], 20, axis=0)
    X_shape = list(Y.shape)
    X_shape.append(4)
    X = np.zeros(X_shape)
    gx, gy, gz = np.mgrid[:Y.shape[0], :Y.shape[1], :Y.shape[2]]
    X[gx, gy, gz, Y] = -1
    X = X + 0.3 * np.random.normal(size=X.shape)
    return X * 100., Y


def main():
    #X, Y = make_dataset_checker_multinomial()
    X, Y = make_dataset_easy_latent_explicit(n_samples=1)
    #X, Y = make_dataset_easy_latent(n_samples=1)
    #X, Y = make_dataset_big_checker_extended()
    #X, Y = make_dataset_big_checker()
    #X, Y = make_dataset_blocks_multinomial(n_samples=5)
    size_y = Y[0].size
    shape_y = Y[0].shape
    n_labels = len(np.unique(Y))
    inds = np.arange(size_y).reshape(shape_y)
    horz = np.c_[inds[:, :-1].ravel(), inds[:, 1:].ravel()]
    vert = np.c_[inds[:-1, :].ravel(), inds[1:, :].ravel()]
    downleft = np.c_[inds[:-1, :-1].ravel(), inds[1:, 1:].ravel()]
    downright = np.c_[inds[:-1, 1:].ravel(), inds[1:, :-1].ravel()]
    edges = np.vstack([horz, vert, downleft, downright]).astype(np.int32)
    graph = sparse.coo_matrix((np.ones(edges.shape[0]),
        (edges[:, 0], edges[:, 1])), shape=(size_y, size_y)).tocsr()
    graph = graph + graph.T

    crf = MultinomialFixedGraphCRFNoBias(n_states=n_labels, graph=graph)
    #crf = MultinomialGridCRF(n_labels=4)
    #clf = StructuredPerceptron(problem=crf, max_iter=50)
    clf = StructuredSVM(problem=crf, max_iter=20, C=1000000, verbose=2,
            check_constraints=True)
    #clf = SubgradientStructuredSVM(problem=crf, max_iter=100, C=10000)
    X_flat = [x.reshape(-1, n_labels).copy("C") for x in X]
    Y_flat = [y.ravel() for y in Y]
    clf.fit(X_flat, Y_flat)
    #clf.fit(X, Y)
    Y_pred = clf.predict(X_flat)
    #Y_pred = clf.predict(X)

    i = 0
    loss = 0
    for x, y, y_pred in zip(X, Y, Y_pred):
        y_pred = y_pred.reshape(x.shape[:2])
        #loss += np.sum(y != y_pred)
        loss += np.sum(np.logical_xor(y, y_pred))
        if i > 4:
            continue
        fig, plots = plt.subplots(1, 4)
        plots[0].imshow(y, interpolation='nearest')
        pw_z = np.zeros((n_labels, n_labels), dtype=np.int32)
        un = (-1000 * x.reshape(-1, n_labels)).astype(np.int32)
        unaries = alpha_expansion_graph(edges, un, pw_z)
        plots[1].imshow(unaries.reshape(y.shape), interpolation='nearest')
        plots[2].imshow(y_pred, interpolation='nearest')
        loss_augmented = clf.problem.loss_augmented_inference(
                x.reshape(-1, n_labels), y.ravel(), clf.w)
        loss_augmented = loss_augmented.reshape(y.shape)
        plots[3].imshow(loss_augmented, interpolation='nearest')
        fig.savefig("data_%03d.png" % i)
        plt.close(fig)
        i += 1
    print("loss: %f" % loss)

if __name__ == "__main__":
    main()

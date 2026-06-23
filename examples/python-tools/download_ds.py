import urllib.request
import gzip
import pickle
import sys

dataset_url = sys.argv[1]
mnist_zipped_name = 'mnist.pkl.gz'
urllib.request.urlretrieve(dataset_url, mnist_zipped_name)
with gzip.open(mnist_zipped_name, 'rb') as f:
    train_set, test_set = pickle.load(f, encoding='latin1')

with open(sys.argv[2], 'wb') as f:
    pickle.dump(train_set, f)

with open(sys.argv[3], 'wb') as f:
    pickle.dump(test_set, f)

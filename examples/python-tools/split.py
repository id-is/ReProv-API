import gzip
import pickle
import sys

print(sys.argv)

dataset = sys.argv[1]
with gzip.open(dataset, 'rb') as f:
    train_set, test_set = pickle.load(f, encoding='latin1')

with open(sys.argv[2], 'wb') as f:
    pickle.dump(train_set, f)

with open(sys.argv[3], 'wb') as f:
    pickle.dump(test_set, f)

import sys
import string
import matplotlib.pyplot as plt


def create_histogram(input_file):
    try:
        with open(input_file, 'r') as f:
            content = f.read()

        histogram = {char: 0 for char in string.ascii_letters + string.digits}

        for char in content:
            if char in histogram:
                histogram[char] += 1

        return histogram

    except FileNotFoundError:
        print("Input file not found!")
        return None


def save_histogram(histogram, output_file):
    # Convert dictionary to lists for plotting
    chars = list(histogram.keys())
    counts = list(histogram.values())

    plt.figure(figsize=(10, 6))
    plt.bar(chars, counts)
    plt.xlabel('Characters')
    plt.ylabel('Count')
    plt.title('Histogram of Letters and Numbers')
    plt.savefig(output_file)  
    plt.close()


histogram = create_histogram(sys.argv[1])
save_histogram(histogram, sys.argv[2])

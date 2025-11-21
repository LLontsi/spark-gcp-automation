#!/usr/bin/env python3
"""
WordCount Application for Apache Spark
Tests the Spark cluster deployment
"""

import sys
from pyspark.sql import SparkSession


def main(input_path, output_path):
    """
    Run WordCount on the input file and save results to output path
    """
    # Create Spark session
    spark = SparkSession.builder \
        .appName("WordCount") \
        .getOrCreate()

    try:
        # Read input file
        text_file = spark.sparkContext.textFile(input_path)

        # WordCount logic
        counts = text_file \
            .flatMap(lambda line: line.split()) \
            .map(lambda word: (word.lower(), 1)) \
            .reduceByKey(lambda a, b: a + b)

        # Sort by count (descending)
        sorted_counts = counts.sortBy(lambda x: x[1], ascending=False)

        # Save results
        sorted_counts.saveAsTextFile(output_path)

        print(f"WordCount completed successfully!")
        print(f"Results saved to: {output_path}")

        # Print top 10 words
        top_words = sorted_counts.take(10)
        print("\nTop 10 words:")
        for word, count in top_words:
            print(f"  {word}: {count}")

    except Exception as e:
        print(f"Error during WordCount execution: {e}")
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: wordcount.py <input_path> <output_path>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    main(input_file, output_file)

# WordCount Application

WordCount test application for validating Apache Spark cluster deployment.

## Usage
```bash
./run_wordcount.sh [input_file] [output_directory]
```

## Example
```bash
# Using default sample text
./run_wordcount.sh

# Using custom input
./run_wordcount.sh /path/to/input.txt /path/to/output
```

## Environment Variables

- `SPARK_MASTER_URL` - Spark master URL (default: spark://spark-master:7077)

## Output

The script will:
1. Create sample input if not provided
2. Submit the WordCount job to Spark
3. Display the top 10 most frequent words
4. Save full results to the output directory

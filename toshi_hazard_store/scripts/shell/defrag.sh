#!/bin/bash

# Define constants
readonly SOURCE="./WORKDIR/ARROW"
# "s3://ths-poc-arrow-test/NZSHM22_RLZ"
readonly TARGET="./WORKDIR/ARROW/HB_RLZ_DFG"
#"s3://ths-dataset-prod/NZSHM22_RLZ"
readonly LOG_DIR="./WORKDIR/LOG"


# make time alias
#readonly time="$time" # ubuntu/debian 
readonly time="/opt/homebrew/bin/gtime" # macosx `brew install gnu-time` 


# Check if the input file was provided as an argument
if [ $# -ne 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

input_file="$1"

# Check if the input file exists and is readable
if [ ! -f "$input_file" ] || [ ! -r "$input_file" ]; then
    echo "Error: Input file '$input_file' does not exist or is not readable."
    exit 1
fi

# Loop through each line in the input file, which represents an id
while IFS= read -r id; do

    # Call the defrag program with the current id as an argument and measure time taken
    echo "Running ths_ds_defrag $id"
    echo "Running ths_ds_defrag $id" >> "$LOG_DIR/defrag.log"
    echo "============================" >> "$LOG_DIR/defrag.log"
    {
        start_time=$(date +%s)  # Record the start time
        $time -f "Time taken for ths_ds_defrag %E" ths_ds_defrag "$SOURCE/$id" "$TARGET" --verbose >> "$LOG_DIR/defrag.log" 2>&1 | grep 'Time taken for' &
        pid=$!
        wait $pid # Wait until the command is done.
        end_time=$(date +%s)  # Record the end time
    } &> /dev/null

    elapsed=$((end_time - start_time))  # Calculate elapsed time in seconds
    echo "Elapsed time: $elapsed seconds"

    if [ $? -ne 0 ]; then
        echo "Error: ths_import extract failed with id '$id'. Exiting loop."
        break
    fi
    echo "Completed ths_ds_defrag $id" >> "$LOG_DIR/defrag.log"
    echo "==============================" >> "$LOG_DIR/defrag.log"

    echo "Processing completed for $id"

done < "$input_file"

echo "All ids processed."

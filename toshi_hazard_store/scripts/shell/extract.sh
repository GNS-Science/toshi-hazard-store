#!/bin/bash

# Define constants
readonly WORKDIR="./WORKDIR"
readonly TARGET="./WORKDIR/ARROW"
# s3://ths-poc-arrow-test/NZSHM22_HB_RLZ" 
readonly LOG_DIR="./WORKDIR/LOG"

# make time alias
#readonly time="/usr/bin/time" # ubuntu/debian 
readonly time="/opt/homebrew/bin/gtime" # macosx `brew install gnu-time` 

#HB count
readonly EXPECTED_RLZ_COUNT="17473560"
# readonly EXPECTED_RLZ_COUNT = 98274384

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

# Loop through each line in the input file, which contains a General Task ID
while IFS= read -r id; do

    encoded_id="${id//\=/\%3D}"

    # Call the first program with the current id as an argument and measure time taken
    echo "Running ths_import producers $id"
    echo "Running ths_import producers $id" >> "$LOG_DIR/producers.log"
    echo "============================" >> "$LOG_DIR/producers.log"
    {
        start_time=$(date +%s)  # Record the start time
        $time -f "Time taken for ths_import %E" ths_import producers "$id" NZSHM22 -W "$WORKDIR" --verbose >> "$LOG_DIR/producers.log" 2>&1 | grep 'Time taken for' &
        pid=$!
        wait $pid # Wait until the command is done.
        if [ $? -ne 0 ]; then
            echo "Error: ths_import producers failed with id '$id'. Exiting loop."
            break
        fi        
        end_time=$(date +%s)  # Record the end time
    } &> /dev/null

    elapsed=$((end_time - start_time))  # Calculate elapsed time in seconds
    echo "Elapsed time: $elapsed seconds"


    echo "Completed ths_import producers $id" >> "$LOG_DIR/producers.log"
    echo "==============================" >> "$LOG_DIR/producers.log"

    # Call the second program with the current id as an argument and measure time taken
    echo "Running ths_import extract $id"
    echo "Running ths_import extract $id" >> "$LOG_DIR/extract.log"
    echo "============================" >> "$LOG_DIR/extract.log"
    {
        start_time=$(date +%s)  # Record the start time
        $time -f "Time taken for ths_import %E" ths_import extract "$id" NZSHM22 -W "$WORKDIR" -O "$TARGET/$id" -CID --verbose >> "$LOG_DIR/extract.log" 2>&1 | grep 'Time taken for' &
        pid=$!
        wait $pid # Wait until the command is done.
        if [ $? -ne 0 ]; then
            echo "Error: ths_import extract failed with id '$id'. Exiting loop."
            break
        fi
        end_time=$(date +%s)  # Record the end time
    } &> /dev/null


    # elapsed=$((end_time - start_time))  # Calculate elapsed time in seconds
    # echo "Elapsed time: $elapsed seconds"

    echo "Completed ths_import extract $id" >> "$LOG_DIR/extract.log"
    echo "==============================" >> "$LOG_DIR/extract.log"

    # Call the third program with the current id as an argument and measure time taken
    echo "Running ths_ds_sanity count-rlz $id"
    echo "Running ths_ds_sanity count-rlz $id" >> "$LOG_DIR/sanity.log"
    echo "============================" >> "$LOG_DIR/sanity.log"
    {
        start_time=$(date +%s)  # Record the start time
        $time -f "Time taken for ths_ds_sanity %E" ths_ds_sanity count-rlz "$TARGET/$id" -x --expected-rlzs $EXPECTED_RLZ_COUNT >> "$LOG_DIR/sanity.log" 2>&1 | grep 'Time taken for' &
        pid=$!
        wait $pid # Wait until the command is done.
        if [ $? -ne 0 ]; then
            echo "Error: ths_ds_sanity count-rlz failed with id '$id'. Exiting loop."
            break
        fi        
        end_time=$(date +%s)  # Record the end time
    } &> /dev/null

    elapsed=$((end_time - start_time))  # Calculate elapsed time in seconds
    echo "Elapsed time: $elapsed seconds"


    echo "Completed ths_ds_sanity count-rlz $id" >> "$LOG_DIR/sanity.log"
    echo "==============================" >> "$LOG_DIR/sanity.log"

    # # clean up space for next ID
    # echo "clearing WORKING space in $WORKDIR/$id"
    # rm -R "$WORKDIR/$id"

    echo "Processing completed for $id"

done < "$input_file"

echo "All ids processed."

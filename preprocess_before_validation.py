import sys

def process_file(input_file, output_file):
    with open(input_file, 'r') as infile:
        lines = infile.readlines()
    
    processed_lines = []
    for line in lines:
        # Replace tabs with four spaces
        line = line.replace('\t', '    ')
        # Remove trailing whitespace
        line = line.rstrip()
        processed_lines.append(line)
    
    with open(output_file, 'w') as outfile:
        for line in processed_lines:
            outfile.write(line + '\n')

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python preprocess-before-validation.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    process_file(input_file, output_file)

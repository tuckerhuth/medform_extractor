import json
import os
import sys

def define_output_structure(file_path):
    """Create the basic dictionary structure for a single file result."""
    return {
        "file_path": file_path,
        "classification": None,
        "confidence": None,
        "metadata": {
            "name": None,
            "date": None,
            "xray_type": None, # Specific to X-ray classification
            # Add other relevant metadata fields as needed
        },
        "extracted_text": None,
        "error": None # Store any processing errors for this file
    }

class ResultManager:
    """Manages writing results incrementally to a JSON file."""
    def __init__(self, output_file):
        self.output_file = output_file
        self._results = self._load_existing_results()

    def _load_existing_results(self):
        """Load existing results if the output file exists and is valid JSON."""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r') as f:
                    # Ensure it's a list, handle empty file or invalid JSON
                    content = f.read()
                    if not content.strip(): # Handle empty file
                        return []
                    data = json.loads(content)
                    if isinstance(data, list):
                        return data
                    else:
                        print(f"Warning: Existing output file '{self.output_file}' does not contain a JSON list. Starting fresh.", file=sys.stderr)
                        return [] # Start fresh if not a list
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from '{self.output_file}'. Starting fresh.", file=sys.stderr)
                return [] # Start fresh if JSON is invalid
            except Exception as e:
                print(f"Warning: Error reading '{self.output_file}': {e}. Starting fresh.", file=sys.stderr)
                return [] # Start fresh on other errors
        return [] # Return empty list if file doesn't exist

    def add_result(self, result_data):
        """Add a single result dictionary and save the updated list to the file."""
        self._results.append(result_data)
        self._save_results()

    def _save_results(self):
        """Save the current list of results to the JSON file."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w') as f:
                json.dump(self._results, f, indent=4)
        except IOError as e:
            print(f"Error: Could not write results to '{self.output_file}': {e}", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred while saving results: {e}", file=sys.stderr)

# Example Usage (optional)
if __name__ == '__main__':
    # Example of how to use the ResultManager
    output_json_path = 'output/scan_results.json'
    manager = ResultManager(output_json_path)

    # Simulate processing two files
    result1 = define_output_structure('data/images/report1.jpg')
    result1['classification'] = 'X-ray'
    result1['metadata']['name'] = 'John Doe'
    result1['metadata']['date'] = '2023-10-26'
    result1['extracted_text'] = 'Sample extracted text for report 1...'

    result2 = define_output_structure('data/images/lab/bloodwork.png')
    result2['classification'] = 'Blood Test'
    result2['metadata']['name'] = 'Jane Smith'
    result2['metadata']['date'] = '2023-10-27'
    result2['extracted_text'] = 'CBC results...'

    result3 = define_output_structure('data/images/unclear.tiff')
    result3['error'] = 'OCR failed due to low quality'

    # Add results one by one
    manager.add_result(result1)
    print(f"Added result for {result1['file_path']}")
    manager.add_result(result2)
    print(f"Added result for {result2['file_path']}")
    manager.add_result(result3)
    print(f"Added result for {result3['file_path']}")

    print(f"Results saved to {os.path.abspath(output_json_path)}") 
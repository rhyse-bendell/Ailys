
import os
from tasks import literature_review

def run_batch_litreview(folder_path, guidance, recall_depth, output_file, assistant=None, callback=None):
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    results = []

    for i, filename in enumerate(pdf_files):
        filepath = os.path.join(folder_path, filename)
        try:
            literature_review.run(
                pdf_path=filepath,
                guidance=guidance,
                recall_depth=recall_depth,
                output_file=output_file
            )
            results.append((filename, "Success"))
        except Exception as e:
            results.append((filename, f"Error: {str(e)}"))
        if callback:
            callback(i + 1, len(pdf_files), filename)

    return results

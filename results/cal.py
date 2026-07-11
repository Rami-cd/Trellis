import json
import os

def calculate_averages(file_path):
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' was not found.")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)

    categories = ["relevance", "correctness", "completeness", "clarity"]
    
    totals = {cat: 0 for cat in categories}
    num_entries = len(data)

    if num_entries == 0:
        print("The JSON file is empty.")
        return

    # Sum up the values
    for entry in data:
        for cat in categories:
            totals[cat] += entry.get(cat, 0)

    # Calculate and display category averages
    print(f"--- Statistics for {num_entries} Entries ---")
    category_averages = []
    
    for cat in categories:
        avg = totals[cat] / num_entries
        category_averages.append(avg)
        print(f"Average {cat.capitalize()}: {avg:.2f}")

    # Calculate the final average of all together
    final_avg = sum(category_averages) / len(category_averages)
    
    print("-" * 30)
    print(f"Final Combined Average: {final_avg:.2f}")

# Run the function
calculate_averages('D:\\Trellis\\results\\v2_nbs_gpt.json')
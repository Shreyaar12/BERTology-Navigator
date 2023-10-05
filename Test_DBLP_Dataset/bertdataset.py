# import torch
# import json
# from transformers import BertTokenizer, BertModel
# from torch.nn.functional import cosine_similarity

# MODEL_NAME = 'bert-base-uncased'
# tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
# model = BertModel.from_pretrained(MODEL_NAME)

# def get_cls_embedding(text):
#     inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
#     with torch.no_grad():
#         outputs = model(**inputs)
#         return outputs.last_hidden_state[0, 0]

# def compare_with_gold(question_str, winning_candidate_value):
#     with open('improveddataset.json', 'r') as f:
#         dataset = json.load(f)    
#     gold_answer = next(
#         (entry['answer']['results']['bindings'][0]['answer']['value'] for entry in dataset['questions'] if entry['question']['string'] == question_str),
#         None)
#     accuracy = 1 if gold_answer == winning_candidate_value else 0
#     return gold_answer, accuracy

# def process_question(entry):
#     labeled_pairs = entry['labeled_pairs']
#     question = entry['question']
#     question_embedding = get_cls_embedding(question)
#     batch_size = 20
#     winning_candidate = None
#     highest_similarity = -1
#     results = []
#     for i in range(0, len(labeled_pairs), batch_size):
#         batch = labeled_pairs[i:i+batch_size]
#         batch_texts = [f"[CLS] {item['s']} [SEP] {item['p']} [SEP] {item['o']}" for item in batch]
#         batch_embeddings = [get_cls_embedding(text) for text in batch_texts]
#         similarities = [cosine_similarity(question_embedding, candidate_embedding, dim=0).item() for candidate_embedding in batch_embeddings]
#         for j, text in enumerate(batch_texts):
#             results.append({
#                 'text': text,
#                 'embedding': batch_embeddings[j].tolist(),
#                 'similarity': similarities[j]
#             })
#         max_similarity = max(similarities)
#         if max_similarity > highest_similarity:
#             highest_similarity = max_similarity
#             winning_candidate = batch[similarities.index(max_similarity)]
#     gold_answer, accuracy = compare_with_gold(question, winning_candidate['o'])
#     return {'question': question,
#         'gold_answer': gold_answer,
#         'accuracy': accuracy,
#         'cosine_similarity': highest_similarity,
#         'winning_candidate': winning_candidate }

# def main():
#     with open('all_labeled_pairs.json', 'r') as f:
#         data = json.load(f)
#     all_results = [process_question(entry) for entry in data['questions']]
#     # Save results
#     with open('all_accuracy_results.json', 'w') as f:
#         json.dump({'results': all_results}, f, indent=4)

# def calculate_overall_accuracy():
#     with open('all_accuracy_results.json', 'r') as f:
#         results_data = json.load(f)
#     accurate_count = sum(1 for entry in results_data['results'] if entry['accuracy'] == 1)
#     total_objects = len(results_data['results'])
#     overall_accuracy = (accurate_count / total_objects) * 100
#     print(f"Overall Accuracy: {overall_accuracy:.2f}%")

# def calculate_overall_accuracy():
#     with open('all_accuracy_results.json', 'r') as f:
#         results_data = json.load(f)    
#     accurate_count = sum(1 for entry in results_data['results'] if entry['accuracy'] == 1)
#     total_objects = len(results_data['results'])
#     overall_accuracy = (accurate_count / total_objects) * 100
#     print(f"Overall Accuracy: {overall_accuracy:.2f}%")

# if __name__ == "__main__":
#     print("execution begin")
#     main()
#     calculate_overall_accuracy()
#     print("execution complete")
import json
import torch
from transformers import BertTokenizer, BertModel
from torch.nn.functional import cosine_similarity
from SPARQLWrapper import SPARQLWrapper, JSON

MODEL_NAME = 'bert-base-uncased'
tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
model = BertModel.from_pretrained(MODEL_NAME)

def get_cls_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        return outputs.last_hidden_state[0, 0]

def fetch_uri_from_label(label):
    """Fetch URI for a given label using SPARQL."""
    sparql = SPARQLWrapper("https://dblp-kg.ltdemos.informatik.uni-hamburg.de/sparql")
    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?resource WHERE {{
            ?resource rdfs:label "{label}" .
        }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    if results['results']['bindings']:
        return results['results']['bindings'][0]['resource']['value']
    return None

def compare_with_gold(question_str, winning_candidate):

    with open('improveddataset.json', 'r') as f:
        dataset = json.load(f)
    
    gold_answers = []
    while winning_candidate != None:
        for entry in dataset['questions']:
            if entry['question']['string'] == question_str or (entry.get('paraphrased_question') and entry['paraphrased_question']['string'] == question_str):
                for binding in entry['answer']['results']['bindings']:
                    if binding['answer']['type']:
                        gold_answers.append(binding['answer']['value'])
                    # print("gold",gold_answers)
                break
    
       
        # process the object
    
        # Check URI
        if all("http" not in winning_candidate[key] for key in ['s', 'p', 'o']) and all("http" in answer for answer in gold_answers):
            o_uri = fetch_uri_from_label(winning_candidate['o'])
            s_uri = fetch_uri_from_label(winning_candidate['s'])
            if o_uri:
                winning_candidate['o'] = o_uri
            if s_uri:
                winning_candidate['s'] = s_uri
    
    accuracy = (1 if (winning_candidate['o']) in gold_answers else 0)  or (1 if (winning_candidate['s']) in gold_answers else 0)

    return gold_answers, accuracy

def process_data():
    # Load data
    with open('labeled_pairs_dataset.json', 'r') as f:
        data = json.load(f)

    all_results = []
    total_count = 0
    correct_count = 0
    for entry in data:
        labeled_pairs = entry['labeled_pairs']
        question = entry['question']
        question_embedding = get_cls_embedding(question)
        highest_similarity = -1
        winning_candidate = None
        for pair in labeled_pairs:
            text = f"[CLS] {pair['s']} [SEP] {pair['p']} [SEP] {pair['o']}"
            candidate_embedding = get_cls_embedding(text)
            similarity = cosine_similarity(question_embedding, candidate_embedding, dim=0).item()
            if similarity > highest_similarity:
                highest_similarity = similarity
                winning_candidate = pair
        gold_answer, accuracy = compare_with_gold(question, winning_candidate)
        total_count += 1
        correct_count += accuracy
        all_results.append({
            'question': question,
            'gold_answer': gold_answer,
            'accuracy': accuracy,
            'cosine_similarity': highest_similarity,
            'winning_candidate': winning_candidate
        })

    with open('comp_accuracy_results.json', 'w') as f:
        json.dump(all_results, f, indent=4)
    return correct_count, total_count

def compute_accuracy():
    correct, total = process_data()
    accuracy = (correct / total) * 100
    print(f"Accuracy: {accuracy:.2f}%")

if __name__ == "__main__":
    print("execution begin")
    process_data()
    # compute_accuracy()
    print("execution complete")


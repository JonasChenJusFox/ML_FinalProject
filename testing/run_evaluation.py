import csv
import time
import os
import sys
from pathlib import Path

# Set up system path to import project modules
TESTING_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTING_DIR.parent
sys.path.append(str(PROJECT_ROOT))

from integration.api import search_restaurants
try:
    from embeddings.query_parser import parse_query
except ImportError:
    print("Warning: Could not import parse_query. Using a dummy parser for evaluation.")
    def parse_query(q): return {}


def load_csv(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(filepath, fieldnames, data):
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def safe_str(val):
    return str(val).lower().strip() if val else ""


def evaluate_parser(input_data):
    results = []
    exact_matches = 0
    total_crashes = 0
    
    for row in input_data:
        q = row['query']
        crashed = 0
        try:
            parsed = parse_query(q)
        except Exception as e:
            print(f"Parser error on '{q}': {e}")
            parsed = {}
            crashed = 1
        
        # Extract predictions safely based on api.py schemas
        pred_price = safe_str(parsed.get('price', ''))
        
        dietary_raw = parsed.get('dietary', [])
        pred_dietary = safe_str(dietary_raw[0] if dietary_raw else '')
        
        cuisine_raw = parsed.get('cuisine', parsed.get('cuisines', []))
        pred_cuisine = safe_str(cuisine_raw[0] if cuisine_raw else '')
        
        loc_raw = parsed.get('location', '')
        if isinstance(loc_raw, dict):
            pred_location = safe_str(loc_raw.get('label', ''))
        else:
            pred_location = safe_str(loc_raw)
            
        # Compare against expected
        exp_price = safe_str(row['expected_price'])
        exp_dietary = safe_str(row['expected_dietary'])
        exp_cuisine = safe_str(row['expected_cuisine'])
        exp_loc = safe_str(row['expected_location'])
        
        p_corr = 1 if (not exp_price or exp_price in pred_price or pred_price in exp_price) else 0
        d_corr = 1 if (not exp_dietary or exp_dietary in pred_dietary or pred_dietary in exp_dietary) else 0
        c_corr = 1 if (not exp_cuisine or exp_cuisine in pred_cuisine or pred_cuisine in exp_cuisine) else 0
        l_corr = 1 if (not exp_loc or exp_loc in pred_location or pred_location in exp_loc) else 0
        
        exact = 1 if (p_corr and d_corr and c_corr and l_corr) else 0
        exact_matches += exact
        total_crashes += crashed
        
        results.append({
            'query': q,
            'expected_price': exp_price, 'pred_price': pred_price, 'price_correct': p_corr,
            'expected_dietary': exp_dietary, 'pred_dietary': pred_dietary, 'dietary_correct': d_corr,
            'expected_cuisine': exp_cuisine, 'pred_cuisine': pred_cuisine, 'cuisine_correct': c_corr,
            'expected_location': exp_loc, 'pred_location': pred_location, 'location_correct': l_corr,
            'exact_match': exact,
            'crashed': crashed
        })
    
    acc = exact_matches / len(input_data) if input_data else 0
    return results, acc, total_crashes


def check_relevance(restaurant, row):
    """Determine constraint match ratio and relevance for a restaurant."""
    search_text = (str(restaurant.get('categories', [])) + " " + 
                   str(restaurant.get('tags', [])) + " " + 
                   str(restaurant.get('name', '')) + " " + 
                   str(restaurant.get('price', '')) + " " + 
                   str(restaurant.get('borough', ''))).lower()
    
    score = 0
    conditions = 0
    
    for field in ['expected_cuisine', 'expected_dietary', 'expected_price']:
        if row.get(field):
            conditions += 1
            if row[field].lower() in search_text: 
                score += 1
                
    if conditions == 0:
        return 1.0, True
        
    ratio = score / conditions
    return ratio, ratio >= 0.5


def evaluate_retrieval_and_latency(input_data):
    sat_results, prec_results, lat_results = [], [], []
    total_sat, total_prec, total_lat = 0, 0, 0
    total_crashes = 0
    
    for row in input_data:
        q = row['query']
        start_time = time.time()
        crashed = 0
        
        try:
            results = search_restaurants(q, filters=None, user_id="anonymous", top_k=5)
        except Exception as e:
            print(f"Search crashed on '{q}': {e}")
            results = []
            crashed = 1
            
        latency_ms = (time.time() - start_time) * 1000
        
        names_list = [r.get('name', 'Unknown') for r in results]
        top_5_names = " | ".join(names_list) if names_list else "No results"
        
        if results:
            relevance_data = [check_relevance(r, row) for r in results]
            avg_constraint_pct = sum(ratio for ratio, _ in relevance_data) / len(results)
            relevant_count = sum(1 for _, is_rel in relevance_data if is_rel)
        else:
            avg_constraint_pct = 0.0
            relevant_count = 0
            
        k = len(results) if len(results) > 0 else 5
        precision = relevant_count / k if k > 0 else 0
        
        sat_results.append({
            'query': q, 'top_k': k, 
            'avg_constraint_match_pct': avg_constraint_pct, 'top_5_restaurants': top_5_names
        })
        prec_results.append({'query': q, 'precision_at_5': precision, 'top_5_restaurants': top_5_names})
        lat_results.append({'query': q, 'total_time_ms': latency_ms})
        
        total_sat += avg_constraint_pct
        total_prec += precision
        total_lat += latency_ms
        total_crashes += crashed
        
    n = len(input_data) if input_data else 1
    return sat_results, prec_results, lat_results, total_sat/n, total_prec/n, total_lat/n, total_crashes


def evaluate_personalization(scenario_data):
    results = []
    total_lift = 0
    total_crashes = 0
    
    for row in scenario_data:
        q = row['query']
        user_id = row['profile_id']
        tags = [t.strip().lower() for t in row['preference_tags'].split(',')]
        crashed = 0
        
        try:
            anon_res = search_restaurants(q, filters=None, user_id="anonymous", top_k=5)
            pers_res = search_restaurants(q, filters=None, user_id=user_id, top_k=5)
        except Exception as e:
            print(f"Personalization search crashed on '{q}': {e}")
            anon_res, pers_res = [], []
            crashed = 1
            
        def calc_tag_match(res_list):
            if not res_list: return 0
            matches = 0
            for r in res_list:
                r_text = (str(r.get('categories', [])) + " " + str(r.get('tags', []))).lower()
                if any(t in r_text for t in tags):
                    matches += 1
            return matches / len(res_list)
            
        anon_score = calc_tag_match(anon_res)
        pers_score = calc_tag_match(pers_res)
        lift = pers_score - anon_score
        total_lift += lift
        total_crashes += crashed
        
        results.append({
            'scenario_id': row['scenario_id'],
            'query': q,
            'anon_pref_match_at_5': anon_score,
            'personalized_pref_match_at_5': pers_score,
            'lift': lift,
            'crashed': crashed
        })
        
    n = len(scenario_data) if scenario_data else 1
    return results, total_lift / n, total_crashes


def main():
    print("Starting NearBite Evaluation Pipeline...\n")
    parser_input_path = TESTING_DIR / 'parser_eval_input.csv'
    scenario_input_path = TESTING_DIR / 'scenario_eval_input.csv'
    
    if not parser_input_path.exists() or not scenario_input_path.exists():
        print("Input CSVs not found! Exiting.")
        return

    parser_data = load_csv(parser_input_path)
    scenario_data = load_csv(scenario_input_path)
    
    print(f"Evaluating Parser Accuracy on {len(parser_data)} queries...")
    parser_res, parser_acc, p_crashes = evaluate_parser(parser_data)
    write_csv(TESTING_DIR / 'parser_eval_results.csv', list(parser_res[0].keys()), parser_res)
    
    print(f"Evaluating Retrieval, Relevance, and Latency on {len(parser_data)} queries...")
    sat_res, prec_res, lat_res, avg_sat, avg_prec, avg_lat, r_crashes = evaluate_retrieval_and_latency(parser_data)
    write_csv(TESTING_DIR / 'filter_satisfaction_results.csv', list(sat_res[0].keys()), sat_res)
    write_csv(TESTING_DIR / 'ranking_precision_results.csv', list(prec_res[0].keys()), prec_res)
    write_csv(TESTING_DIR / 'latency_results.csv', list(lat_res[0].keys()), lat_res)
    
    print(f"Evaluating Personalization Lift on {len(scenario_data)} scenarios...")
    pers_res, avg_lift, pers_crashes = evaluate_personalization(scenario_data)
    write_csv(TESTING_DIR / 'personalization_lift_results.csv', list(pers_res[0].keys()), pers_res)
    
    total_app_crashes = p_crashes + r_crashes + pers_crashes

    # Export Summary Metrics
    summary = [
        {'metric': 'parser_exact_match_accuracy', 'value': f"{parser_acc:.2%}"},
        {'metric': 'avg_constraint_match@5', 'value': f"{avg_sat:.2%}"},
        {'metric': 'avg_precision@5', 'value': f"{avg_prec:.2%}"},
        {'metric': 'avg_personalization_lift@5', 'value': f"{avg_lift:.2%}"},
        {'metric': 'avg_latency_ms', 'value': f"{avg_lat:.2f}"},
        {'metric': 'total_crashes', 'value': str(total_app_crashes)}
    ]
    write_csv(TESTING_DIR / 'summary_metrics.csv', ['metric', 'value'], summary)
    
    # Update Markdown Evaluation Report
    report_path = TESTING_DIR / 'evaluation_report.md'
    if report_path.exists():
        content = report_path.read_text(encoding='utf-8')
        content = content.replace('{parser_acc}', f"{parser_acc:.2%}")
        content = content.replace('{avg_sat}', f"{avg_sat:.2%}")
        content = content.replace('{avg_prec}', f"{avg_prec:.2%}")
        content = content.replace('{avg_lift}', f"{avg_lift:.2%}")
        content = content.replace('{avg_lat}', f"{avg_lat:.2f} ms")
        content = content.replace('{total_crashes}', str(total_app_crashes))
        report_path.write_text(content, encoding='utf-8')
    
    print("\n=== Evaluation Complete ===")
    print(f"Parser Exact Match Accuracy : {parser_acc:.2%}")
    print(f"Avg Constraint Match @5     : {avg_sat:.2%}")
    print(f"Avg Precision @5            : {avg_prec:.2%}")
    print(f"Avg Personalization Lift @5 : {avg_lift:.2%}")
    print(f"Avg Latency                 : {avg_lat:.2f} ms")
    print(f"Total Test Crashes          : {total_app_crashes}")
    print(f"\nAll output artifacts saved successfully in {TESTING_DIR}")

if __name__ == "__main__":
    main()
import ast
from flask import Flask, request, jsonify
import sqlite3
import re

app = Flask(__name__)

# Database setup
def init_db():
    # Connect to SQLite database and create a table for storing rules
    conn = sqlite3.connect('rules.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        rule_string TEXT)''')
    conn.commit()
    conn.close()

# Initialize the DB when the app starts
init_db()

# Function to evaluate rule with provided data
def evaluate_rule_with_data(rule_string, data):
    try:
        # Replace placeholders (e.g., age, department) in rule_string with actual values
        for key, value in data.items():
            # Ensure that strings are enclosed in quotes
            if isinstance(value, str):
                value = f"'{value}'"
            rule_string = re.sub(rf"\b{key}\b", str(value), rule_string)

        # Safely evaluate the rule using eval
        result = eval(rule_string)
        return result
    except Exception as e:
        print(f"Error during evaluation: {e}")
        return False

# API to create a rule
@app.route('/api/create-rule', methods=['POST'])
def create_rule():
    data = request.get_json()

    # Check if 'rule' key is present in the incoming request
    if 'rule' not in data:
        return jsonify({"error": "Missing 'rule' in request"}), 400

    rule = data['rule']
    conn = sqlite3.connect('rules.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rules (rule_string) VALUES (?)", (rule,))
    conn.commit()
    rule_id = cursor.lastrowid
    conn.close()
    return jsonify({"ruleId": rule_id})

# API to evaluate a rule
@app.route('/api/evaluate-rule', methods=['POST'])
def evaluate_rule():
    rule_id = request.json['ruleId']
    data = request.json['data']
    conn = sqlite3.connect('rules.db')
    cursor = conn.cursor()
    cursor.execute("SELECT rule_string FROM rules WHERE id=?", (rule_id,))
    rule_string = cursor.fetchone()
    
    if rule_string is None:
        return jsonify({"error": "Rule not found"}), 404
    
    rule_string = rule_string[0]
    conn.close()
    
    # Evaluate the rule with the provided data
    result = evaluate_rule_with_data(rule_string, data)
    
    return jsonify({"result": result})

def evaluate_rule_with_data(rule_string, data):
    try:
        # Replace SQL-like operators with Python equivalents
        rule_string = rule_string.replace("AND", "and").replace("OR", "or")
        
        # Print the rule for debugging
        print(f"Evaluating rule: {rule_string}")
        
        # Safely evaluate the rule using Python's eval, passing the data context
        tree = ast.parse(rule_string, mode='eval')
        code = compile(tree, filename="<ast>", mode="eval")
        return eval(code, {}, data)
    except Exception as e:
        print(f"Error evaluating rule: {e}")
        return False

# API to combine rules
@app.route('/api/combine-rules', methods=['POST'])
def combine_rules():
    rule_ids = request.json['ruleIds']
    conn = sqlite3.connect('rules.db')
    cursor = conn.cursor()
    
    combined_rule = []
    
    for rule_id in rule_ids:
        cursor.execute("SELECT rule_string FROM rules WHERE id=?", (rule_id,))
        result = cursor.fetchone()
        
        if result is None:
            return jsonify({"error": f"Rule ID {rule_id} not found"}), 404
        
        combined_rule.append(result[0])
    
    # Combine the rules using ' OR ' between them
    combined_rule_string = ' OR '.join(f'({rule})' for rule in combined_rule)

    # Create the combined rule in the database
    cursor.execute("INSERT INTO rules (rule_string) VALUES (?)", (combined_rule_string,))
    conn.commit()
    combined_rule_id = cursor.lastrowid
    conn.close()
    
    return jsonify({"ruleId": combined_rule_id})

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=5001)
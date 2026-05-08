from flask import Flask, request, jsonify, render_template
from journal_engine import generate_journal_entry
from database import init_db, save_entry, get_recent_entries, delete_entry, clear_all_entries

app = Flask(__name__)

# Initialise database on startup
init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    transaction = data.get("transaction", "").strip()

    if not transaction:
        return jsonify({"success": False, "error": "Transaction text is required."}), 400

    result = generate_journal_entry(transaction)

    if result["success"]:
        result["id"] = save_entry(result)

    return jsonify(result)


@app.route("/api/entries", methods=["GET"])
def entries():
    limit = int(request.args.get("limit", 10))
    return jsonify(get_recent_entries(limit))


@app.route("/api/entries/<int:entry_id>", methods=["DELETE"])
def delete(entry_id):
    success = delete_entry(entry_id)
    return jsonify({"success": success})


@app.route("/api/entries/clear", methods=["POST"])
def clear():
    clear_all_entries()
    return jsonify({"success": True})


if __name__ == "__main__":
    import os

app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000))
)
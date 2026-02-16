import urllib.parse

# ==========================================
# ENTER YOUR CREDENTIALS HERE
# ==========================================
username = "YOUR_USERNAME_HERE"
password = "YOUR_RAW_PASSWORD_HERE"  # Put your actual password here, exactly as it is
cluster_address = "cluster0.abcde.mongodb.net" # Replace with your actual cluster address (from Atlas)
database_name = "ai_service"
# ==========================================

# URL encode the username and password
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)

# Construct the URI
uri = f"mongodb+srv://{encoded_username}:{encoded_password}@{cluster_address}/{database_name}?retryWrites=true&w=majority"

print("\n" + "="*50)
print("COPY THIS INTO YOUR .env FILE:")
print("="*50 + "\n")
print(f"MONGO_URI={uri}")
print("\n" + "="*50)

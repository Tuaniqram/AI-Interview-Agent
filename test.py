from app.config.database import get_supabase


db = get_supabase()


result = db.table(
    "companies"
).insert({

    "name":"Test Company",

    "website":"https://example.com",

    "description":"Software company"

}).execute()


print(result.data)
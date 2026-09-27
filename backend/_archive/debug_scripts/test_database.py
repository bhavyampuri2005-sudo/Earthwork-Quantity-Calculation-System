from services.chainage_service import ChainageService

service = ChainageService()

records = [

    {
        "project_id": 1,
        "chainage": 80320,
        "gl": 372.458,
        "fl": 375.973,
        "fill": 3.515,
        "cut": 0.0
    },

    {
        "project_id": 1,
        "chainage": 80340,
        "gl": 372.462,
        "fl": 375.980,
        "fill": 3.518,
        "cut": 0.0
    }

]

count = service.save_records(records)

print("\n----------------------------")
print(f"Inserted Records : {count}")
print("----------------------------")
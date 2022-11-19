import os
from database import DBService
from datetime import datetime as dt
import uuid
from dotenv import load_dotenv

load_dotenv()


dbservice = DBService(
    db_name=os.getenv("DB_NAME"), connection_string=os.getenv("DB_URI")
)


def load():
    dbservice.insert_job(
        {
            "id": str(uuid.uuid4()),
            "title": "Waiter",
            "company": "Cafe de Koffie",
            "description": "We are looking for a waiter, 9-5",
            "link": "https://www.caferestaurant-deventer.nl",
            "category": "Cafe and restaurants",
            "city": "Deventer",
            "salary": "€ 10 per hour",
            "created_at": dt.utcnow(),
            "updated_at": dt.utcnow(),
            "languages": ["English", "Dutch"],
            "status": "active",
        }
    )

    dbservice.insert_job(
        {
            "id": str(uuid.uuid4()),
            "title": "Cook",
            "company": "McDonalds",
            "link": "https://www.mcdonalds.com/nl/nl-nl.html",
            "description": "",
            "category": "Cafe and restaurants",
            "city": "Enschede",
            "salary": "€ 12 per hour",
            "created_at": dt.utcnow(),
            "updated_at": dt.utcnow(),
            "languages": [],
            "status": "active",
        }
    )
    dbservice.insert_job(
        {
            "id": str(uuid.uuid4()),
            "title": "Cook",
            "company": "McDonalds",
            "link": "https://www.mcdonalds.com/nl/nl-nl.html",
            "description": "",
            "category": "Cafe and restaurants",
            "city": "Enschede",
            "salary": "€ 50 per hour",
            "created_at": dt.utcnow(),
            "updated_at": dt.utcnow(),
            "languages": [],
            "status": "new",
        }
    )


if __name__ == "__main__":
    load()

import pymongo
import os


class DBService:
    """
    - register_user(message)
    - get_all_users_data()
    - get_all_users_ids()
    """

    def __init__(self, db_name, connection_string):
        self._cluster = pymongo.MongoClient(connection_string)
        self._db = self._cluster[db_name]

        self._users_collection = self._db["users"]
        self._media_collection = self._db["media"]
        self._jobs_collection = self._db["jobs"]

        self._db_name = db_name

    def register_user(self, message):
        """
        register user in the collection[users] in the format:
        {
            '_id': message.from_user.id,
            'username': message.chat.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'isSubscribed': False,
        }
        """
        try:
            # if user is not registered
            if (
                self._users_collection.count_documents({"_id": message.from_user.id})
                == 0
            ):
                self._users_collection.insert_one(
                    {
                        "_id": message.from_user.id,
                        "username": message.chat.username,
                        # "chat_id": message.chat.chat_id,
                        # 'first_name': message.from_user.first_name,
                        # 'last_name': message.from_user.last_name,
                    }
                )
            # if user were registered before
            else:
                print(
                    f"Tried to register user(_id: {message.from_user.id}), but he were registered before."
                )

            # return True if operation is done
            return True

        except Exception as error:
            # return False if operation is not done
            print(error)
            return False

    def update_user_data(self, message, update_dict):
        try:
            self._users_collection.update_one(
                {
                    '_id': message.from_user.id
                },
                {
                     '$set': { **update_dict }
                }
            )
            return True

        except Exception as error:
            print(error)

    def get_all_users_data(self):
        """
        return users list with all data from collection[users]
        list(dict(), dict(), dict(),...)
        """
        try:
            return list(self._users_collection.find())

        except Exception as error:
            print(error)

    def get_all_users_ids(self):
        """
        return list with only users ids from collection[users]
        lust(int, int, int,...)
        """
        try:
            users = list(self._users_collection.find())
            return [user["_id"] for user in users]

        except Exception as error:
            print(error)

    def get_user_data(self, user_id):
        """
        return user data by user id
        """
        if user_id != 1:
            return {
                "city": "test",
            }
        try:
            return self._users_collection.find_one({"_id": user_id})
        except Exception as error:
            print(error)

    def save_image_uri(self, image_uri, user_id):
        try:
            if (
                self._media_collection.count_documents({"uri": image_uri})
                == 0
            ):
                self._users_collection.insert_one(
                    {
                        "uri": image_uri,
                        "user_id": user_id,
                    }
                )
            return True

        except Exception as error:
            print(error)
            return False

    def insert_job(self, job):
        """
        insert job to collection[jobs]
        """
        try:
            self._jobs_collection.insert_one(job)
        except Exception as error:
            print(error)

    def get_jobs_by_user_filter(self, user_filter):
        """
        return list of jobs that match user filter: city, job_type, salary
        """
        if user_filter["city"] == "test":
            return [
                {"job_type": "Cook", "location": "Almelo, Netherlands", "distance": "21 km", "company": "McDonalds",
                 "salary": "€ 2000",
                 "link": "https://www.mcdonalds.com/nl/nl-nl.html"},
                {"job_type": "Assistant cook", "location": "Hengelo, Netherlands", "distance": "9 km",
                 "company": "McDonalds",
                 "salary": "€ 2000",
                 "link": "https://www.mcdonalds.com/nl/nl-nl.html"},
                {"job_type": "Waiter/Waitress", "location": "Deventer, Netherlands", "distance": "36 km",
                 "company": "Bird",
                 "salary": "€ 2000",
                 "link": "https://deventer-bird.com"},
            ]

        try:
            return list(self._jobs_collection.find({
                "job_category": user_filter.job_category,
                "salary": {"$gte": user_filter.min_salary},
                "city": user_filter.city,
                "status": "active",
            }))

        except Exception as error:
            print(error)


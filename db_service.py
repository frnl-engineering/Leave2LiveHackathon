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

    def update_user_data(self, message):
        try:
            self._users_collection.update_one(
                {
                    '_id': message.from_user.id
                },
                {
                     '$set': {
                        'username': 'tested',
                        'new_field': '2',
                        'list_field': [],
                        }
                }, 
                upsert=False, multi=False
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
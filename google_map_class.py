import os
import re
import googlemaps
import logging
logger = logging.getLogger('GoogleMapsClass')


class GoogleMapsClass:
    def __init__(self):
        self.gmaps = googlemaps.Client(key=os.getenv('GM_API_KEY'))
        self.letters_dict = {
            "К": "K",
            "Е": "E",
            "Х": "X",
            "В": "B",
            "А": "A",
            "Р": "P",
            "О": "O",
            "С": "C",
            "М": "M",
        }

    def find_address_from_input(self, input_postcode):
        input_postcode = self.prepare_postcode(input_postcode)
        postcode_is_correct = self.postcode_is_correct(input_postcode)

        found_places = self.gmaps.find_place("Netherlands " + input_postcode, input_type='textquery')['candidates']
        found_addresses = []
        for place_ids_dic in found_places:
            my_place_id = place_ids_dic['place_id']
            place = self.gmaps.place(place_id=my_place_id)
            dicts_results = place['result']['address_components']
            city_list = [dict_['long_name'] for dict_ in dicts_results if 'locality' in dict_['types']]
            country_code_list = [dict_['short_name'] for dict_ in dicts_results if 'country' in dict_['types']]
            formatted_postcode_list = [dict_['short_name'] for dict_ in dicts_results if
                                       'postal_code' in dict_['types']]
            query_type_list_nonflat = [dict_['types'] for dict_ in dicts_results]
            query_type_list = [item for sublist in query_type_list_nonflat for item in sublist]
            location = place['result']['geometry']['location']
            if (
                    'postal_code' in query_type_list and
                    'NL' in country_code_list and
                    city_list and
                    location and
                    formatted_postcode_list
            ):
                coordinates = f"{str(location['lat'])}, {str(location['lng'])}"
                found_addresses.append(
                    {
                        'city': city_list[0],
                        'formatted_postcode': formatted_postcode_list[0],
                        'coordinates': coordinates
                    }
                )
                return found_addresses, postcode_is_correct

        if self.postcode_is_correct:
            logger.warning("index code lookup error: index='%s'; found_places='%s'", input_postcode, found_places)

        return found_addresses, postcode_is_correct

    def prepare_postcode(self, input_postcode: str) -> str:
        postcode = ""
        if not input_postcode:
            return ""

        for c in input_postcode.upper():
            if c == ' ':
                continue

            if c in self.letters_dict:
                postcode += self.letters_dict[c]
            else:
                postcode += c

        if len(postcode) >= 6:
            postcode = postcode[0:4] + " " + postcode[4:]

        return postcode

    def postcode_is_correct(self, postcode: str) -> bool:
        x = re.search("^[0-9]{4} [A-Z]{2}$", postcode)

        return x is not None

import os
from dotenv import load_dotenv

SOUTHWARK_PARK_IDS = {
    'court1': "ad7d3c7b-9dff-4442-bb18-4761970f11c0",
    'court2': "f942cbed-3f8a-4828-9afc-2c0a23886ffa",
    'court3': "7626935c-1e38-49ca-a3ff-52205ed98a81",
    'court4': "1d7ac83f-5fdb-4fe4-a743-5383b7a1641f"
}

TANNER_PARK_IDS = {
    'court1': "339f226f-f6e7-4b44-92b3-70eacf6c7169",
    'court2': "d1ce3582-411e-4f78-aad4-5442c764d07a",
    'court3': "f802edcc-1d08-494b-8378-1153d7ef3e1c",
    'court4': "ad18619f-5c70-475d-942b-ae1c4dbe4739"
}

QUEENS_PARK_IDS = {
    'court1': "cbd8fd03-7bd7-4994-8b40-59820ade1c54",
    'court2': "e1a25134-52b1-4ef2-a289-faaa63a076e2",
    'court3': "60a1ac3c-be49-4db7-bf68-f9b23e207d6f",
    'court4': "88d45e6e-5378-45ad-a2ae-62c8712751af",
    'court5': "f81df548-d5c4-4fd0-943d-7e74d29b6fe0",
    'court6': "5d3342ab-82fb-4b02-9da1-edf1fd595212"
}

TAG = "a"
ATTR = "data-test-id"

TANNER_URL = "https://clubspark.lta.org.uk/TannerStPark/Booking/BookByDate"
SOUTHWARK_URL = "https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate"
QUEENS_URL = "https://clubspark.lta.org.uk/QueensParkTennisCourts/Booking/BookByDate"

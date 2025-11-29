from app import create_app
from models.models import db, ParkingLot

app = create_app()

with app.app_context():
    lots = ParkingLot.query.all()
    for lot in lots:
        print(f"Lot: {lot.name}")
        for spot in lot.spots:
            print(f"  Slot: {spot.slot_number}, Booked: {spot.is_booked}")

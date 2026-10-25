"""Renders the e-ticket PDF with a QR code (FR-TKT-03)."""

from io import BytesIO

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.clock import IST
from app.schemas.booking import BookingOut

INK = colors.HexColor("#0f2747")
MUTED = colors.HexColor("#555555")
RULE = colors.HexColor("#b5b5b5")
SHADE = colors.HexColor("#eef4fb")


def rupees(paise: int) -> str:
    # The built-in PDF fonts have no rupee glyph, so tickets use "Rs".
    whole, rem = divmod(paise, 100)
    return f"Rs {whole:,}" if rem == 0 else f"Rs {whole:,}.{rem:02d}"


def qr_image(booking: BookingOut) -> Image:
    payload = "|".join(
        [
            "BERTH",
            booking.pnr or "",
            booking.train_number,
            booking.journey_date.isoformat(),
            booking.from_station.code,
            booking.to_station.code,
            booking.travel_class,
        ]
    )
    img = qrcode.make(payload, box_size=6, border=1)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=32 * mm, height=32 * mm)


def render_ticket(booking: BookingOut) -> bytes:
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=MUTED)
    label = ParagraphStyle("label", parent=small, fontSize=7.5, leading=9)
    value = ParagraphStyle("value", parent=styles["Normal"], fontSize=10.5, leading=13)
    title = ParagraphStyle(
        "title", parent=styles["Title"], fontSize=16, textColor=INK, alignment=0, spaceAfter=2
    )

    dep = booking.departure_at.astimezone(IST)
    arr = booking.arrival_at.astimezone(IST)

    def cell(caption: str, text: str) -> list[Paragraph]:
        return [Paragraph(caption.upper(), label), Paragraph(text, value)]

    header = Table(
        [
            [
                [
                    Paragraph("Berth e-ticket", title),
                    Paragraph("Electronic reservation slip", small),
                    Spacer(1, 4 * mm),
                    *cell("PNR", f"<b>{booking.pnr}</b>"),
                    *cell("Booking status", str(booking.status)),
                ],
                qr_image(booking),
            ]
        ],
        colWidths=[130 * mm, 40 * mm],
    )
    header.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")])
    )

    journey = Table(
        [
            [
                cell("Train", f"{booking.train_number} {booking.train_name}"),
                cell("Class", str(booking.travel_class)),
                cell("Distance", f"{booking.distance_km} km"),
            ],
            [
                cell("From", f"{booking.from_station.name} ({booking.from_station.code})"),
                cell("Departure", dep.strftime("%d %b %Y, %H:%M")),
                cell("Journey date", booking.journey_date.strftime("%d %b %Y")),
            ],
            [
                cell("To", f"{booking.to_station.name} ({booking.to_station.code})"),
                cell("Arrival", arr.strftime("%d %b %Y, %H:%M")),
                cell("Booked on", booking.created_at.astimezone(IST).strftime("%d %b %Y")),
            ],
        ],
        colWidths=[75 * mm, 50 * mm, 45 * mm],
    )
    journey.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SHADE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    rows = [["#", "Name", "Age", "Gender", "Booking status", "Current status"]]
    for p in booking.passengers:
        rows.append(
            [
                str(p.seq_no),
                p.name,
                str(p.age),
                str(p.gender),
                p.booking_status or "",
                p.current_status,
            ]
        )
    passengers = Table(rows, colWidths=[8 * mm, 52 * mm, 12 * mm, 16 * mm, 40 * mm, 42 * mm])
    passengers.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                ("BACKGROUND", (0, 0), (-1, 0), SHADE),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    fare_rows = [["Total fare", rupees(booking.total_fare_paise)]]
    if booking.refunded_paise:
        fare_rows.append(["Refunded", rupees(booking.refunded_paise)])
    fare = Table(fare_rows, colWidths=[40 * mm, 40 * mm], hAlign="RIGHT")
    fare.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
                ("FONT", (1, 0), (1, 0), "Helvetica-Bold", 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )

    notes = Paragraph(
        "Carry a valid photo ID while travelling. Status abbreviations: CNF confirmed "
        "(coach/berth/type), WL waitlisted, CAN cancelled.<br/>"
        "<b>Berth is a CSC702 course project. Payments are simulated and this ticket is "
        "not valid for travel.</b>",
        small,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Berth e-ticket {booking.pnr}",
        author="Berth",
    )
    doc.build(
        [
            header,
            Spacer(1, 6 * mm),
            journey,
            Spacer(1, 6 * mm),
            passengers,
            Spacer(1, 4 * mm),
            fare,
            Spacer(1, 8 * mm),
            notes,
        ]
    )
    return buf.getvalue()

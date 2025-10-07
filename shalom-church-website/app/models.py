from app import db

class Member(db.Model):
    __tablename__ = 'members'

    member_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    date_joined = db.Column(db.DateTime, nullable=False)

    # PostgreSQL ENUMs must have a name
    baptism_status = db.Column(
        db.Enum('Not Baptized', 'Baptized Here', 'Baptized Elsewhere', name='baptism_status_enum'),
        default='Not Baptized',
        nullable=False
    )
    membership_status = db.Column(
        db.Enum('Active', 'Inactive', 'Visitor', name='membership_status_enum'),
        default='Visitor',
        nullable=False
    )

    profile_picture_url = db.Column(db.String(500))
    
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def __repr__(self):
        return f"<Member {self.first_name} {self.last_name}>"

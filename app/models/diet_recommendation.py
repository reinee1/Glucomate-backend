from app.extensions import db

class DietRecommendation(db.Model):
    __tablename__ = "diet_recommendation"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    text = db.Column(db.Text, nullable=False)
    valid_from = db.Column(db.Date, nullable=True)
    valid_until = db.Column(db.Date, nullable=True)

    user = db.relationship("User", backref=db.backref("diet_recommendations", cascade="all,delete-orphan"))

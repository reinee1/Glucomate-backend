from alembic import op
import sqlalchemy as sa

revision = 'bb89beaf1a3d'
down_revision = '848844c3b5ba'
branch_labels = None
depends_on = None

def upgrade():
    # Only convert if it's currently BOOLEAN
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='weekly_assessments'
          AND column_name='medication_adherence'
          AND data_type='boolean'
      ) THEN
        ALTER TABLE weekly_assessments
          ALTER COLUMN medication_adherence DROP DEFAULT;

        ALTER TABLE weekly_assessments
          ALTER COLUMN medication_adherence TYPE INTEGER
          USING CASE
            WHEN medication_adherence IS TRUE  THEN 1
            WHEN medication_adherence IS FALSE THEN 0
            ELSE NULL
          END;
      END IF;
    END
    $$;
    """)

def downgrade():
    # Only convert back if it's currently INTEGER
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='weekly_assessments'
          AND column_name='medication_adherence'
          AND data_type='integer'
      ) THEN
        ALTER TABLE weekly_assessments
          ALTER COLUMN medication_adherence DROP DEFAULT;

        ALTER TABLE weekly_assessments
          ALTER COLUMN medication_adherence TYPE BOOLEAN
          USING CASE
            WHEN medication_adherence IS NULL THEN NULL
            WHEN medication_adherence = 0     THEN FALSE
            ELSE TRUE
          END;
      END IF;
    END
    $$;
    """)

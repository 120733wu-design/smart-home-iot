from models.database import query, execute


class BuzzerModel:

    @staticmethod
    def get_or_create(device_id):
        row = query(
            "SELECT * FROM buzzer_config WHERE device_id = %s",
            (device_id,), fetchone=True
        )
        if row:
            return row
        execute(
            "INSERT INTO buzzer_config (device_id, mode, manual_state) VALUES (%s, 'auto', 0)",
            (device_id,)
        )
        return query(
            "SELECT * FROM buzzer_config WHERE device_id = %s",
            (device_id,), fetchone=True
        )

    @staticmethod
    def get_by_device_key(device_key):
        return query(
            """SELECT bc.* FROM buzzer_config bc
               JOIN devices d ON bc.device_id = d.id
               WHERE d.device_key = %s""",
            (device_key,), fetchone=True
        )

    @staticmethod
    def set_mode(device_id, mode):
        if mode in ('manual', 'mute'):
            execute(
                "UPDATE buzzer_config SET mode=%s, manual_state=0 WHERE device_id=%s",
                (mode, device_id)
            )
        else:
            execute(
                "UPDATE buzzer_config SET mode=%s WHERE device_id=%s",
                (mode, device_id)
            )

    @staticmethod
    def set_manual_state(device_id, state):
        execute(
            "UPDATE buzzer_config SET manual_state=%s WHERE device_id=%s",
            (state, device_id)
        )

    @staticmethod
    def ensure_exists(device_id):
        row = query(
            "SELECT id FROM buzzer_config WHERE device_id=%s",
            (device_id,), fetchone=True
        )
        if not row:
            execute(
                "INSERT INTO buzzer_config (device_id, mode, manual_state) VALUES (%s, 'auto', 0)",
                (device_id,)
            )

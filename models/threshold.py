from models.database import query, execute


class ThresholdModel:
    """设备阈值配置，直接读写 devices 表内置阈值列"""

    # sensor_type → devices 表列名映射
    _COLUMN_MAP = {
        'temperature': ('threshold_temp_min', 'threshold_temp_max'),
        'humidity':    ('threshold_humi_min', 'threshold_humi_max'),
        'light':       (None, 'threshold_light_max'),  # light 只有上限
    }

    @staticmethod
    def set(device_id, sensor_type, min_value=None, max_value=None):
        """更新 devices 表中对应传感器的阈值列"""
        cols = ThresholdModel._COLUMN_MAP.get(sensor_type)
        if not cols:
            return False

        min_col, max_col = cols
        if min_col and min_value is not None:
            execute(f"UPDATE devices SET {min_col} = %s WHERE id = %s", (min_value, device_id))
        if max_col and max_value is not None:
            execute(f"UPDATE devices SET {max_col} = %s WHERE id = %s", (max_value, device_id))
        return True

    @staticmethod
    def get_by_device(device_id, sensor_type):
        """从 devices 表读取阈值，返回 {min_value, max_value} 字典"""
        cols = ThresholdModel._COLUMN_MAP.get(sensor_type)
        if not cols:
            return None

        min_col, max_col = cols
        fields = []
        if min_col:
            fields.append(f"{min_col} AS min_value")
        else:
            fields.append("NULL AS min_value")
        if max_col:
            fields.append(f"{max_col} AS max_value")
        else:
            fields.append("NULL AS max_value")

        sql = f"SELECT {', '.join(fields)} FROM devices WHERE id = %s LIMIT 1"
        row = query(sql, (device_id,), fetchone=True)
        if not row:
            return None
        return {
            'min_value': float(row['min_value']) if row.get('min_value') is not None else None,
            'max_value': float(row['max_value']) if row.get('max_value') is not None else None,
        }

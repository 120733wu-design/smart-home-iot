CREATE DATABASE IF NOT EXISTS smart_home CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_home;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','user') DEFAULT 'user',
    face_feature TEXT NULL COMMENT '单账号仅存储一组人脸特征，重复录入自动覆盖',
    face_enabled TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    device_key VARCHAR(50) NOT NULL UNIQUE,
    type ENUM('sensor','actuator','hybrid') DEFAULT 'sensor',
    status ENUM('online','offline') DEFAULT 'offline',
    location VARCHAR(100) DEFAULT '',
    threshold_temp_min DECIMAL(5,1) DEFAULT 5.0,
    threshold_temp_max DECIMAL(5,1) DEFAULT 35.0,
    threshold_humi_min DECIMAL(5,1) DEFAULT 20.0,
    threshold_humi_max DECIMAL(5,1) DEFAULT 80.0,
    threshold_light_max DECIMAL(6,1) DEFAULT 900.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sensor_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    sensor_type ENUM('temperature','humidity','light') NOT NULL,
    value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) DEFAULT '',
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dst (device_id,sensor_type,recorded_at),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    alert_type ENUM('threshold','disconnection','anomaly') NOT NULL,
    severity ENUM('info','warning','critical') DEFAULT 'warning',
    message VARCHAR(255) NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS control_commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    command VARCHAR(100) NOT NULL,
    params JSON DEFAULT NULL,
    status ENUM('pending','sent','acknowledged','failed') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ml_predictions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    sensor_type ENUM('temperature','humidity') NOT NULL,
    predicted_value DECIMAL(10,2) NOT NULL,
    confidence DECIMAL(5,2) DEFAULT NULL,
    predicted_at DATETIME NOT NULL,
    model_type ENUM('linear_regression','random_forest') DEFAULT 'linear_regression',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
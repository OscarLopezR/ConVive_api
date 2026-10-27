-- PROYECTO: MATCHMAKING DE INQUILINOS Y ARRENDADORES
-- SGBD: MySQL / MariaDB

-- Reinicia la base para poder ejecutar este script las veces necesarias.
-- ADVERTENCIA: borra todos los datos de db_vivienda.
DROP DATABASE IF EXISTS db_vivienda;
CREATE DATABASE db_vivienda CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_vivienda;

-- 1. TABLA ROL 

CREATE TABLE ROL (
    idRol INT AUTO_INCREMENT,
    nombreRol VARCHAR(30) NOT NULL UNIQUE,
    descripcionRol VARCHAR(255),
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT PK_ROL
        PRIMARY KEY (idRol)
);

-- 2. TABLA USUARIO

CREATE TABLE USUARIO (
    ID INT AUTO_INCREMENT,
    nombreDeUsuario VARCHAR(60) NOT NULL UNIQUE,
    nombre VARCHAR(50) NOT NULL,
    paterno VARCHAR(50) NOT NULL,
    materno VARCHAR(50),
    email VARCHAR(100) NOT NULL UNIQUE,
    claveDeUsuario VARCHAR(255) NOT NULL, -- hash bcrypt, nunca texto plano
    telefono VARCHAR(15),
    foto VARCHAR(255),
    fecha_nacimiento DATE,
    habilitado BOOLEAN NOT NULL DEFAULT TRUE,
    bloqueado BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT PK_USUARIO
        PRIMARY KEY (ID)
);

-- 3. TABLA USUARIO_ROL 

CREATE TABLE USUARIO_ROL (
    idUsuario INT NOT NULL,
    idRol INT NOT NULL,

    CONSTRAINT PK_USUARIO_ROL
        PRIMARY KEY (idUsuario, idRol),

    CONSTRAINT FK_USUARIOROL_USUARIO
        FOREIGN KEY (idUsuario)
        REFERENCES USUARIO(ID)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT FK_USUARIOROL_ROL
        FOREIGN KEY (idRol)
        REFERENCES ROL(idRol)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- 4. TABLA TOKEN_RECUPERACION (recuperar contrasena)

CREATE TABLE TOKEN_RECUPERACION (
    ID INT AUTO_INCREMENT,
    token_hash CHAR(64) NOT NULL UNIQUE, -- SHA-256 del token enviado por correo
    expira DATETIME NOT NULL,
    usado BOOLEAN NOT NULL DEFAULT FALSE,
    ID_usuario INT NOT NULL,

    CONSTRAINT PK_TOKEN_RECUPERACION
        PRIMARY KEY (ID),

    CONSTRAINT FK_TOKEN_USUARIO
        FOREIGN KEY (ID_usuario)
        REFERENCES USUARIO(ID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- 5. TABLA PERFIL

CREATE TABLE PERFIL (
    ID INT AUTO_INCREMENT,
    ocupacion VARCHAR(100),
    mascotas BOOLEAN NOT NULL DEFAULT FALSE,
    habito_limpieza VARCHAR(50),
    frecuencia_visitas VARCHAR(50),
    horario_actividad VARCHAR(50),
    ID_usuario INT NOT NULL,

    CONSTRAINT PK_PERFIL
        PRIMARY KEY (ID),

    CONSTRAINT FK_PERFIL_USUARIO
        FOREIGN KEY (ID_usuario)
        REFERENCES USUARIO(ID)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT UQ_PERFIL_USUARIO
        UNIQUE (ID_usuario)
);

-- 6. TABLA PREFERENCIAS

CREATE TABLE PREFERENCIAS (
    ID INT AUTO_INCREMENT,
    mascotas BOOLEAN NOT NULL DEFAULT FALSE,
    edad_minima INT,
    edad_maxima INT,
    genero_preferido VARCHAR(30),
    -- Preferencias del arrendador sobre su companero (NULL = indistinto / no aplica)
    ocupacion_preferida VARCHAR(20),
    horario_preferido VARCHAR(20),
    limpieza_preferida VARCHAR(20),
    visitas_permitidas VARCHAR(20),
    mascotas_permitidas VARCHAR(20),
    fumar BOOLEAN,
    ID_usuario INT NOT NULL,

    CONSTRAINT PK_PREFERENCIAS
        PRIMARY KEY (ID),

    CONSTRAINT FK_PREFERENCIAS_USUARIO
        FOREIGN KEY (ID_usuario)
        REFERENCES USUARIO(ID)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT UQ_PREFERENCIAS_USUARIO
        UNIQUE (ID_usuario),

    CONSTRAINT CK_EDAD_PREFERENCIAS
        CHECK (edad_minima IS NULL OR edad_maxima IS NULL
               OR edad_minima <= edad_maxima)
);


-- 7. TABLA HABITACION

CREATE TABLE HABITACION (
    ID INT AUTO_INCREMENT,
    titulo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL,
    metros DECIMAL(6,2),
    disponibilidad BOOLEAN NOT NULL DEFAULT TRUE,
    reglas TEXT,

    serv_agua BOOLEAN NOT NULL DEFAULT FALSE,
    serv_luz BOOLEAN NOT NULL DEFAULT FALSE,
    serv_internet BOOLEAN NOT NULL DEFAULT FALSE,
    serv_gas BOOLEAN NOT NULL DEFAULT FALSE,

    calle VARCHAR(100),
    interior VARCHAR(20),
    exterior VARCHAR(20),
    colonia VARCHAR(100),
    delegacion VARCHAR(100),
    estado VARCHAR(100),
    c_p VARCHAR(10),

    ID_arrendador INT NOT NULL,

    CONSTRAINT PK_HABITACION
        PRIMARY KEY (ID),

    CONSTRAINT FK_HABITACION_ARRENDADOR
        FOREIGN KEY (ID_arrendador)
        REFERENCES USUARIO(ID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT CK_HABITACION_PRECIO
        CHECK (precio >= 0),

    CONSTRAINT CK_HABITACION_METROS
        CHECK (metros IS NULL OR metros > 0)
);

-- 8. TABLA FOTOGRAFIAS

CREATE TABLE FOTOGRAFIAS (
    ID INT AUTO_INCREMENT,
    principal BOOLEAN NOT NULL DEFAULT FALSE,
    url_fotografias VARCHAR(500) NOT NULL,
    ID_habitacion INT NOT NULL,

    CONSTRAINT PK_FOTOGRAFIAS
        PRIMARY KEY (ID),

    CONSTRAINT FK_FOTOGRAFIAS_HABITACION
        FOREIGN KEY (ID_habitacion)
        REFERENCES HABITACION(ID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- 9. TABLA SOLICITUD

CREATE TABLE SOLICITUD (
    ID INT AUTO_INCREMENT,
    estado_tramite ENUM(
        'PENDIENTE',
        'ACEPTADA',
        'RECHAZADA',
        'CANCELADA'
    ) NOT NULL DEFAULT 'PENDIENTE',

    mensaje TEXT,
    porcentaje DECIMAL(5,2),
    fecha_postulacion DATE NOT NULL,
    fecha_fin DATE,

    ID_inquilino INT NOT NULL,
    ID_habitacion INT NOT NULL,

    CONSTRAINT PK_SOLICITUD
        PRIMARY KEY (ID),

    CONSTRAINT FK_SOLICITUD_INQUILINO
        FOREIGN KEY (ID_inquilino)
        REFERENCES USUARIO(ID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT FK_SOLICITUD_HABITACION
        FOREIGN KEY (ID_habitacion)
        REFERENCES HABITACION(ID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT CK_SOLICITUD_PORCENTAJE
        CHECK (porcentaje IS NULL OR
               (porcentaje >= 0 AND porcentaje <= 100)),

    CONSTRAINT CK_SOLICITUD_FECHAS
        CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_postulacion)
);

-- 10. TABLA CONTRATO

CREATE TABLE CONTRATO (
    ID INT AUTO_INCREMENT,
    pago_mes DECIMAL(10,2) NOT NULL,
    deposito DECIMAL(10,2) NOT NULL,
    estado ENUM(
        'ACTIVO',
        'FINALIZADO',
        'CANCELADO'
    ) NOT NULL DEFAULT 'ACTIVO',

    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,

    ID_solicitud INT NOT NULL,

    CONSTRAINT PK_CONTRATO
        PRIMARY KEY (ID),

    CONSTRAINT FK_CONTRATO_SOLICITUD
        FOREIGN KEY (ID_solicitud)
        REFERENCES SOLICITUD(ID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT UQ_CONTRATO_SOLICITUD
        UNIQUE (ID_solicitud),

    CONSTRAINT CK_CONTRATO_PAGO
        CHECK (pago_mes >= 0),

    CONSTRAINT CK_CONTRATO_DEPOSITO
        CHECK (deposito >= 0),

    CONSTRAINT CK_CONTRATO_FECHAS
        CHECK (fecha_fin > fecha_inicio)
);

-- 11. TABLA EVALUACION

CREATE TABLE EVALUACION (
    ID INT AUTO_INCREMENT,
    calificacion TINYINT NOT NULL,
    comentarios TEXT,
    fecha DATE NOT NULL,

    ID_evaluador INT NOT NULL,
    ID_evaluado INT NOT NULL,
    ID_contrato INT NOT NULL,

    CONSTRAINT PK_EVALUACION
        PRIMARY KEY (ID),

    CONSTRAINT FK_EVALUACION_EVALUADOR
        FOREIGN KEY (ID_evaluador)
        REFERENCES USUARIO(ID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT FK_EVALUACION_EVALUADO
        FOREIGN KEY (ID_evaluado)
        REFERENCES USUARIO(ID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT FK_EVALUACION_CONTRATO
        FOREIGN KEY (ID_contrato)
        REFERENCES CONTRATO(ID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT CK_EVALUACION_CALIFICACION
        CHECK (calificacion BETWEEN 1 AND 5),

    CONSTRAINT CK_EVALUACION_USUARIOS
        CHECK (ID_evaluador <> ID_evaluado),

    CONSTRAINT UQ_EVALUACION
        UNIQUE (ID_evaluador, ID_contrato)
);

-- 9. TABLA DOCUMENTO_PDF

CREATE TABLE DOCUMENTO_PDF (
    ID INT AUTO_INCREMENT,
    tipo_documento VARCHAR(50) NOT NULL,
    url_archivo VARCHAR(255) NOT NULL,
    fecha_generacion DATETIME NOT NULL,
    ID_contrato INT NOT NULL,

    CONSTRAINT PK_DOCUMENTO_PDF 
        PRIMARY KEY (ID),

    CONSTRAINT FK_DOCUMENTO_CONTRATO 
        FOREIGN KEY (ID_contrato) 
        REFERENCES CONTRATO(ID) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);

-- 12. TABLA REGISTRO_CORREO

CREATE TABLE REGISTRO_CORREO (
    ID INT AUTO_INCREMENT,
    asunto VARCHAR(150) NOT NULL,
    destinatario VARCHAR(100) NOT NULL,
    estado_envio ENUM('PENDIENTE', 'ENVIADO', 'FALLIDO') NOT NULL DEFAULT 'PENDIENTE',
    fecha_envio DATETIME NOT NULL,
    ID_usuario INT NOT NULL,

    CONSTRAINT PK_REGISTRO_CORREO 
        PRIMARY KEY (ID),

    CONSTRAINT FK_REGISTRO_USUARIO 
        FOREIGN KEY (ID_usuario) 
        REFERENCES USUARIO(ID) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);

-- POBLAR TABLA USUARIO

INSERT INTO ROL (nombreRol, descripcionRol) VALUES
('INQUILINO', 'Busca una habitacion compatible con su estilo de vida'),
('ARRENDADOR', 'Publica habitaciones y recibe solicitudes');

-- claveDeUsuario es un marcador: ejecuta `python -m app.seed` para asignar
-- el hash bcrypt real (contrasena de prueba: Convive123).
INSERT INTO USUARIO
(nombreDeUsuario, nombre, paterno, materno, email, claveDeUsuario, telefono, foto, fecha_nacimiento)
VALUES
('carlos.h', 'Carlos', 'Hernandez', 'Lopez',
 'carlos.h@email.com', 'PENDIENTE_SEED',
 '5512345678', 'carlos.jpg', '2003-04-12'),

('ana.m', 'Ana', 'Martinez', 'Garcia',
 'ana.m@email.com', 'PENDIENTE_SEED',
 '5523456789', 'ana.jpg', '1992-08-20'),

('luis.r', 'Luis', 'Ramirez', 'Torres',
 'luis.r@email.com', 'PENDIENTE_SEED',
 '5534567890', 'luis.jpg', '1988-01-30'),

('sofia.g', 'Sofia', 'Gomez', 'Perez',
 'sofia.g@email.com', 'PENDIENTE_SEED',
 '5545678901', 'sofia.jpg', '2002-11-05');

INSERT INTO USUARIO_ROL (idUsuario, idRol) VALUES
(1, 1), (2, 2), (3, 2), (4, 1);

-- 11. POBLAR TABLA PERFIL

INSERT INTO PERFIL
(ocupacion, mascotas, habito_limpieza,
 frecuencia_visitas, horario_actividad, ID_usuario)
VALUES
('Estudiante', FALSE, 'Alto',
 'Baja', 'Diurno', 1),

('Arquitecta', TRUE, 'Alto',
 'Media', 'Diurno', 2),

('Ingeniero', FALSE, 'Medio',
 'Baja', 'Nocturno', 3),

('Estudiante', TRUE, 'Alto',
 'Media', 'Diurno', 4);


-- 12. POBLAR TABLA PREFERENCIAS

INSERT INTO PREFERENCIAS
(mascotas, edad_minima, edad_maxima,
 genero_preferido, ID_usuario)
VALUES
(FALSE, 20, 30, 'Indistinto', 1),

(TRUE, 22, 35, 'Indistinto', 2),

(FALSE, 20, 35, 'Indistinto', 3),

(TRUE, 20, 30, 'Indistinto', 4);

-- 13. POBLAR TABLA HABITACION

INSERT INTO HABITACION
(titulo, descripcion, precio, metros, disponibilidad,
 reglas, serv_agua, serv_luz, serv_internet, serv_gas,
 calle, interior, exterior, colonia, delegacion, estado, c_p,
 ID_arrendador)
VALUES
(
 'Habitación cerca de ESCOM',
 'Habitación amueblada ideal para estudiante.',
 4500.00,
 16.50,
 TRUE,
 'No fumar. Mantener limpieza.',
 TRUE, TRUE, TRUE, TRUE,
 'Av. Instituto Politécnico Nacional',
 '3A',
 NULL,
 'Lindavista',
 'Gustavo A. Madero',
 'Ciudad de México',
 '07300',
 2
),

(
 'Habitación económica',
 'Habitación privada con acceso a internet.',
 3800.00,
 14.00,
 TRUE,
 'No fiestas. No fumar.',
 TRUE, TRUE, TRUE, FALSE,
 'Calzada de Ticomán',
 '2B',
 NULL,
 'Santa María Ticomán',
 'Gustavo A. Madero',
 'Ciudad de México',
 '07330',
 3
),

(
 'Habitación amplia',
 'Habitación amplia y luminosa para estudiante o profesionista.',
 5200.00,
 20.00,
 TRUE,
 'No mascotas. No fiestas.',
 TRUE, TRUE, TRUE, TRUE,
 'Av. Montevideo',
 '4C',
 NULL,
 'Lindavista',
 'Gustavo A. Madero',
 'Ciudad de México',
 '07300',
 2
);


-- 14. POBLAR TABLA FOTOGRAFIAS

INSERT INTO FOTOGRAFIAS
(principal, url_fotografias, ID_habitacion)
VALUES
(TRUE, 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQZJrP8Lb57851X0dHYxCYBDSm-PxKIqKaIgqRlgaLCcFLdSKJzha9z9Knr&s=10', 1),

(FALSE, 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQZJrP8Lb57851X0dHYxCYBDSm-PxKIqKaIgqRlgaLCcFLdSKJzha9z9Knr&s=10', 1),

(TRUE, 'https://es.habcdn.com/photos/project/medium/habitacion-vacia-1718539.jpg', 2),

(TRUE, 'https://img.pikbest.com/wp/202345/spacious-contemporary-room-with-window-a-3d-render_9615507.jpg!w700wp', 3);


-- =========================================================
-- 15. POBLAR TABLA SOLICITUD
-- =========================================================

INSERT INTO SOLICITUD
(estado_tramite, mensaje, porcentaje,
 fecha_postulacion, fecha_fin,
 ID_inquilino, ID_habitacion)
VALUES
(
 'ACEPTADA',
 'Estoy interesado en la habitación y soy estudiante.',
 92.50,
 '2026-09-01',
 '2026-09-05',
 1,
 1
),

(
 'ACEPTADA',
 'Me interesa la habitación por su ubicación.',
 87.00,
 '2026-09-02',
 '2026-09-06',
 4,
 2
),

(
 'PENDIENTE',
 'Quisiera conocer más información sobre la habitación.',
 78.50,
 '2026-09-03',
 NULL,
 1,
 3
);

-- 16. POBLAR TABLA CONTRATO

INSERT INTO CONTRATO
(pago_mes, deposito, estado,
 fecha_inicio, fecha_fin, ID_solicitud)
VALUES
(
 4500.00,
 4500.00,
 'ACTIVO',
 '2026-09-10',
 '2027-09-10',
 1
),

(
 3800.00,
 3800.00,
 'ACTIVO',
 '2026-09-15',
 '2027-09-15',
 2
),

(
 5200.00,
 5200.00,
 'CANCELADO',
 '2026-08-01',
 '2027-08-01',
 3
);
-- 17. POBLAR TABLA EVALUACION

INSERT INTO EVALUACION
(calificacion, comentarios, fecha,
 ID_evaluador, ID_evaluado, ID_contrato)
VALUES
(
 5,
 'El arrendador fue atento y cumplió con lo acordado.',
 '2026-09-11',
 1,
 2,
 1
),

(
 5,
 'El inquilino mantuvo una buena comunicación y cumplió sus pagos.',
 '2026-09-11',
 2,
 1,
 1
),

(
 4,
 'Buena experiencia y comunicación durante el proceso.',
 '2026-09-11',
 4,
 3,
 2
);
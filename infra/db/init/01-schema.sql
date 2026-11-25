-- HR-Datenbank der fiktiven Firma "Kranich Software GmbH".
-- Alle Personen, Adressen und Zahlen sind frei erfunden.

CREATE TABLE employees (
    id                 integer PRIMARY KEY,
    name               text     NOT NULL,
    title              text     NOT NULL,          -- Stellenbezeichnung, wie auf der Visitenkarte
    role               text     NOT NULL,          -- Rollen-Gruppe, Grundlage für Gehaltsstatistiken
    team               text     NOT NULL,
    office             text     NOT NULL,
    email              text     NOT NULL UNIQUE,
    manager_id         integer  REFERENCES employees (id),
    bio                text     NOT NULL DEFAULT '',  -- Freitext, von Mitarbeitenden selbst gepflegt

    -- ===== Ab hier: sensible Daten, die ein KI-Agent nie sehen soll =====
    salary             integer  NOT NULL,          -- Jahresbruttogehalt in Euro
    home_address       text     NOT NULL,
    performance_rating smallint NOT NULL CHECK (performance_rating BETWEEN 1 AND 5),
    sick_days          smallint NOT NULL           -- Krankheitstage im laufenden Jahr
);

-- Gehälter OHNE Namen und IDs: Grundlage für anonymisierte Statistiken.
-- (Ob das wirklich anonym ist, klären wir in der Übung ...)
CREATE VIEW salary_facts AS
    SELECT role, team, office, salary
    FROM employees;

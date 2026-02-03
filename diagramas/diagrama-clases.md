# Diagrama de Clases - CASTOR ELECCIONES

## 1. Vista General de Paquetes

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ARQUITECTURA DE PAQUETES                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   castor                                             │
│                                                                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐         │
│  │    core_service     │  │    e14_service      │  │  dashboard_service  │         │
│  │                     │  │                     │  │                     │         │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │         │
│  │  │    models     │  │  │  │    models     │  │  │  │    models     │  │         │
│  │  └───────────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │         │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │         │
│  │  │   services    │  │  │  │   services    │  │  │  │   services    │  │         │
│  │  └───────────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │         │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │         │
│  │  │    routes     │  │  │  │    routes     │  │  │  │    routes     │  │         │
│  │  └───────────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │         │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │         │
│  │  │    schemas    │  │  │  │    schemas    │  │  │  │    schemas    │  │         │
│  │  └───────────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │         │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │         │
│  │  │    utils      │  │  │  │    utils      │  │  │  │    utils      │  │         │
│  │  └───────────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │         │
│  │                     │  │                     │  │                     │         │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘         │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              shared                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │   config    │  │  database   │  │    cache    │  │  exceptions │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Service - Diagrama de Clases

### 2.1 Modelos (Entities)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            CORE SERVICE - MODELS                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────────────────┐
                              │         <<abstract>>            │
                              │           BaseModel             │
                              ├─────────────────────────────────┤
                              │ + id: UUID                      │
                              │ + created_at: datetime          │
                              │ + updated_at: datetime          │
                              ├─────────────────────────────────┤
                              │ + save(): None                  │
                              │ + delete(): None                │
                              │ + to_dict(): dict               │
                              └───────────────┬─────────────────┘
                                              │
                                              │ extends
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
│          User             │ │         Session           │ │          Lead             │
├───────────────────────────┤ ├───────────────────────────┤ ├───────────────────────────┤
│ - email: str              │ │ - user_id: UUID           │ │ - user_id: UUID           │
│ - password_hash: str      │ │ - token: str              │ │ - name: str               │
│ - full_name: str          │ │ - device: str             │ │ - email: str              │
│ - role: UserRole          │ │ - ip_address: str         │ │ - phone: str              │
│ - organization: str       │ │ - expires_at: datetime    │ │ - company: str            │
│ - is_active: bool         │ │ - is_valid: bool          │ │ - source: str             │
│ - last_login: datetime    │ │                           │ │ - status: LeadStatus      │
├───────────────────────────┤ ├───────────────────────────┤ │ - notes: str              │
│ + set_password(pwd): None │ │ + invalidate(): None      │ ├───────────────────────────┤
│ + check_password(pwd): bool│ + is_expired(): bool      │ │ + update_status(s): None  │
│ + get_sessions(): List    │ │ + refresh(): Session      │ │ + assign_to(user): None   │
│ + update_last_login(): None│                           │ └───────────────────────────┘
└─────────────┬─────────────┘ └───────────────────────────┘
              │
              │ 1
              │
              │ *
              ▼
┌───────────────────────────┐
│       UserSettings        │
├───────────────────────────┤
│ - user_id: UUID           │
│ - theme: str              │
│ - language: str           │
│ - notifications: bool     │
│ - timezone: str           │
├───────────────────────────┤
│ + update(data): None      │
└───────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                                    ENUMS
═══════════════════════════════════════════════════════════════════════════════════════

┌───────────────────┐          ┌───────────────────┐
│   <<enumeration>> │          │   <<enumeration>> │
│     UserRole      │          │    LeadStatus     │
├───────────────────┤          ├───────────────────┤
│ ADMIN             │          │ NEW               │
│ ANALYST           │          │ CONTACTED         │
│ OBSERVER          │          │ QUALIFIED         │
│ VIEWER            │          │ CONVERTED         │
└───────────────────┘          │ LOST              │
                               └───────────────────┘
```

### 2.2 Services

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CORE SERVICE - SERVICES                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│         <<interface>>               │
│        IAuthService                 │
├─────────────────────────────────────┤
│ + login(email, pwd): TokenPair      │
│ + logout(token): bool               │
│ + refresh(token): TokenPair         │
│ + validate(token): User             │
└─────────────────┬───────────────────┘
                  │
                  │ implements
                  ▼
┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│           AuthService               │          │          TokenService               │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - db: Session                       │          │ - secret_key: str                   │
│ - token_service: TokenService       │◆────────>│ - algorithm: str = "HS256"          │
│ - cache: Redis                      │          │ - access_ttl: int = 3600            │
├─────────────────────────────────────┤          │ - refresh_ttl: int = 86400          │
│ + login(email, pwd): TokenPair      │          ├─────────────────────────────────────┤
│ + logout(token): bool               │          │ + generate_access(user): str        │
│ + refresh(token): TokenPair         │          │ + generate_refresh(user): str       │
│ + validate(token): User             │          │ + decode(token): dict               │
│ + register(data): User              │          │ + verify(token): bool               │
│ - _hash_password(pwd): str          │          │ - _create_payload(user): dict       │
│ - _verify_password(pwd, hash): bool │          └─────────────────────────────────────┘
└─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│           UserService               │          │          LeadService                │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - db: Session                       │          │ - db: Session                       │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + get_by_id(id): User               │          │ + create(data): Lead                │
│ + get_by_email(email): User         │          │ + get_all(filters): List[Lead]      │
│ + create(data): User                │          │ + get_by_id(id): Lead               │
│ + update(id, data): User            │          │ + update(id, data): Lead            │
│ + delete(id): bool                  │          │ + delete(id): bool                  │
│ + list_all(filters): List[User]     │          │ + assign(id, user_id): Lead         │
│ + change_role(id, role): User       │          │ + change_status(id, status): Lead   │
│ + deactivate(id): User              │          └─────────────────────────────────────┘
└─────────────────────────────────────┘
```

### 2.3 Schemas (DTOs)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CORE SERVICE - SCHEMAS                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────┐     ┌───────────────────────────┐
│   <<pydantic>>            │     │   <<pydantic>>            │
│   LoginRequest            │     │   LoginResponse           │
├───────────────────────────┤     ├───────────────────────────┤
│ + email: EmailStr         │     │ + access_token: str       │
│ + password: str           │     │ + refresh_token: str      │
└───────────────────────────┘     │ + token_type: str = "bearer"
                                  │ + expires_in: int         │
┌───────────────────────────┐     └───────────────────────────┘
│   <<pydantic>>            │
│   RegisterRequest         │     ┌───────────────────────────┐
├───────────────────────────┤     │   <<pydantic>>            │
│ + email: EmailStr         │     │   UserResponse            │
│ + password: str           │     ├───────────────────────────┤
│ + full_name: str          │     │ + id: UUID                │
│ + organization: str       │     │ + email: str              │
└───────────────────────────┘     │ + full_name: str          │
                                  │ + role: UserRole          │
┌───────────────────────────┐     │ + organization: str       │
│   <<pydantic>>            │     │ + is_active: bool         │
│   TokenPair               │     │ + created_at: datetime    │
├───────────────────────────┤     └───────────────────────────┘
│ + access_token: str       │
│ + refresh_token: str      │
└───────────────────────────┘
```

---

## 3. E-14 Service - Diagrama de Clases

### 3.1 Modelos Electorales

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         E-14 SERVICE - ELECTORAL MODELS                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────┐          ┌───────────────────────────┐
│        Election           │          │          Party            │
├───────────────────────────┤          ├───────────────────────────┤
│ + id: UUID                │          │ + id: UUID                │
│ + name: str               │          │ + name: str               │
│ + election_date: date     │          │ + abbreviation: str       │
│ + election_type: ElectionType        │ + logo_url: str           │
│ + status: ElectionStatus  │          │ + color: str              │
│ + country: str            │          ├───────────────────────────┤
├───────────────────────────┤          │ + get_candidates(): List  │
│ + get_contests(): List    │          └─────────────┬─────────────┘
│ + is_active(): bool       │                        │
└─────────────┬─────────────┘                        │
              │                                      │
              │ 1                                    │ 1
              │                                      │
              │ *                                    │ *
              ▼                                      │
┌───────────────────────────┐                        │
│         Contest           │                        │
├───────────────────────────┤                        │
│ + id: UUID                │                        │
│ + election_id: UUID       │                        │
│ + name: str               │                        │
│ + contest_type: ContestType                        │
│ + jurisdiction: str       │                        │
│ + total_seats: int        │                        │
├───────────────────────────┤                        │
│ + get_candidates(): List  │                        │
│ + get_results(): dict     │                        │
└─────────────┬─────────────┘                        │
              │                                      │
              │ 1                                    │
              │                                      │
              │ *                                    │
              ▼                                      │
┌───────────────────────────┐                        │
│        Candidate          │◄───────────────────────┘
├───────────────────────────┤
│ + id: UUID                │
│ + contest_id: UUID        │
│ + party_id: UUID          │
│ + full_name: str          │
│ + document_id: str        │
│ + ballot_number: int      │
│ + photo_url: str          │
│ + is_active: bool         │
├───────────────────────────┤
│ + get_votes(): int        │
│ + get_party(): Party      │
└───────────────────────────┘
```

### 3.2 Modelos Geográficos

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         E-14 SERVICE - GEOGRAPHY MODELS                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────┐
│       Department          │
├───────────────────────────┤
│ + id: UUID                │
│ + code: str               │  ◄── DIVIPOLA
│ + name: str               │
├───────────────────────────┤
│ + get_municipalities(): List
└─────────────┬─────────────┘
              │
              │ 1
              │ *
              ▼
┌───────────────────────────┐
│      Municipality         │
├───────────────────────────┤
│ + id: UUID                │
│ + department_id: UUID     │
│ + code: str               │  ◄── DIVIPOLA
│ + name: str               │
│ + risk_level: RiskLevel   │
│ + population: int         │
├───────────────────────────┤
│ + get_stations(): List    │
│ + get_risk_color(): str   │
└─────────────┬─────────────┘
              │
              │ 1
              │ *
              ▼
┌───────────────────────────┐
│     PollingStation        │
├───────────────────────────┤
│ + id: UUID                │
│ + municipality_id: UUID   │
│ + code: str               │
│ + name: str               │
│ + address: str            │
│ + latitude: Decimal       │
│ + longitude: Decimal      │
│ + total_tables: int       │
├───────────────────────────┤
│ + get_tables(): List      │
│ + get_coordinates(): tuple│
└─────────────┬─────────────┘
              │
              │ 1
              │ *
              ▼
┌───────────────────────────┐
│      PollingTable         │
├───────────────────────────┤
│ + id: UUID                │
│ + station_id: UUID        │
│ + contest_id: UUID        │
│ + table_number: int       │
│ + registered_voters: int  │
├───────────────────────────┤
│ + get_forms(): List       │
│ + get_reconciliation(): Reconciliation
└───────────────────────────┘
```

### 3.3 Modelos de Formularios y OCR

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          E-14 SERVICE - FORM MODELS                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│           FormInstance              │
├─────────────────────────────────────┤
│ + id: UUID                          │
│ + polling_table_id: UUID            │
│ + uploaded_by: UUID                 │
│ + form_type: FormType               │
│ + source_type: SourceType           │
│ + file_url: str                     │
│ + file_hash: str                    │
│ + processing_status: ProcessingStatus
│ + ocr_confidence: Decimal           │
│ + processed_at: datetime            │
├─────────────────────────────────────┤
│ + get_ocr_fields(): List[OCRField]  │
│ + get_vote_tallies(): List[VoteTally]
│ + get_validations(): List[ValidationResult]
│ + get_discrepancies(): List[Discrepancy]
│ + needs_review(): bool              │
│ + mark_as_validated(): None         │
└───────────────┬─────────────────────┘
                │
    ┌───────────┼───────────┬───────────────────┐
    │           │           │                   │
    │ 1         │ 1         │ 1                 │ 1
    │           │           │                   │
    │ *         │ *         │ *                 │ *
    ▼           ▼           ▼                   ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐
│ OCRField  │ │ VoteTally │ │Validation │ │  Discrepancy  │
│           │ │           │ │  Result   │ │               │
├───────────┤ ├───────────┤ ├───────────┤ ├───────────────┤
│+id: UUID  │ │+id: UUID  │ │+id: UUID  │ │+id: UUID      │
│+form_id   │ │+form_id   │ │+form_id   │ │+form_id       │
│+field_name│ │+candidate │ │+rule_id   │ │+field_name    │
│+raw_value │ │+votes: int│ │+passed:bool│+expected_value│
│+parsed    │ │+null_votes│ │+message   │ │+actual_value  │
│+confidence│ │+blank_votes│+severity  │ │+difference    │
│+bbox:JSONB│ │+total     │ └───────────┘ │+severity      │
│+page_num  │ │+source    │               │+resolved: bool│
├───────────┤ ├───────────┤               │+resolved_by   │
│+is_valid()│ │+validate()│               ├───────────────┤
└───────────┘ └───────────┘               │+resolve(user) │
                                          └───────────────┘
```

### 3.4 Modelos de Alertas y Auditoría

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       E-14 SERVICE - ALERT & AUDIT MODELS                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐      ┌─────────────────────────────────────┐
│        ValidationRule               │      │          Alert                      │
├─────────────────────────────────────┤      ├─────────────────────────────────────┤
│ + id: UUID                          │      │ + id: UUID                          │
│ + name: str                         │      │ + form_id: UUID                     │
│ + description: str                  │      │ + discrepancy_id: UUID              │
│ + rule_type: str                    │      │ + alert_type: str                   │
│ + expression: str                   │      │ + severity: AlertSeverity           │
│ + severity: AlertSeverity           │      │ + status: AlertStatus               │
│ + is_active: bool                   │      │ + title: str                        │
├─────────────────────────────────────┤      │ + message: str                      │
│ + evaluate(data): bool              │      │ + acknowledged_by: UUID             │
│ + get_error_message(): str          │      │ + acknowledged_at: datetime         │
└─────────────────────────────────────┘      │ + resolved_by: UUID                 │
                                             │ + resolved_at: datetime             │
                                             ├─────────────────────────────────────┤
┌─────────────────────────────────────┐      │ + acknowledge(user): None           │
│        Reconciliation               │      │ + resolve(user, notes): None        │
├─────────────────────────────────────┤      │ + is_critical(): bool               │
│ + id: UUID                          │      └─────────────────────────────────────┘
│ + polling_table_id: UUID            │
│ + contest_id: UUID                  │
│ + winning_form_id: UUID             │      ┌─────────────────────────────────────┐
│ + status: ReconciliationStatus      │      │       AuditLog                      │
│ + final_votes: dict (JSONB)         │      ├─────────────────────────────────────┤
│ + notes: str                        │      │ + id: UUID                          │
│ + reconciled_by: UUID               │      │ + user_id: UUID                     │
│ + reconciled_at: datetime           │      │ + form_id: UUID                     │
├─────────────────────────────────────┤      │ + action: AuditAction               │
│ + set_winner(form): None            │      │ + entity_type: str                  │
│ + finalize(): None                  │      │ + entity_id: UUID                   │
│ + dispute(): None                   │      │ + old_values: dict (JSONB)          │
└─────────────────────────────────────┘      │ + new_values: dict (JSONB)          │
                                             │ + ip_address: str                   │
                                             │ + user_agent: str                   │
                                             │ + created_at: datetime              │
                                             ├─────────────────────────────────────┤
                                             │ # IMMUTABLE - No update/delete      │
                                             │ + to_dict(): dict                   │
                                             └─────────────────────────────────────┘
```

### 3.5 Services E-14

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           E-14 SERVICE - SERVICES                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│         <<interface>>               │
│         IOCRProvider                │
├─────────────────────────────────────┤
│ + extract_text(image): str          │
│ + extract_cells(image): List[Cell]  │
│ + get_confidence(): float           │
└─────────────────┬───────────────────┘
                  │
                  │ implements
                  ▼
┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│       ClaudeOCRAdapter              │          │         E14OCRService               │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - api_key: str                      │          │ - ocr_provider: IOCRProvider        │
│ - model: str                        │          │ - db: Session                       │
│ - max_tokens: int                   │          │ - config: E14Config                 │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + extract_text(image): str          │◄─────────│ + process_form(file): FormResult    │
│ + extract_cells(image): List[Cell]  │          │ + parallel_ocr(files): List         │
│ + get_confidence(): float           │          │ + extract_vote_tallies(data): List  │
│ - _encode_image(img): str           │          │ - _preprocess_image(img): bytes     │
│ - _parse_response(resp): dict       │          │ - _save_results(result): None       │
└─────────────────────────────────────┘          └─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│       ValidationService             │          │         AlertService                │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - rules: List[ValidationRule]       │          │ - db: Session                       │
│ - alert_service: AlertService       │◆────────>│ - notification_svc: NotificationSvc │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + validate(form): ValidationResult  │          │ + create(severity, type, msg): Alert│
│ + check_arithmetic(votes): bool     │          │ + acknowledge(id, user): None       │
│ + detect_discrepancies(forms): List │          │ + resolve(id, user, notes): None    │
│ + compare_sources(sources): Diff    │          │ + list_open(): List[Alert]          │
│ - _apply_rule(rule, data): bool     │          │ + list_by_severity(sev): List       │
│ - _create_discrepancy(diff): None   │          │ - _notify_stakeholders(alert): None │
└─────────────────────────────────────┘          └─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│     ReconciliationService           │          │        AuditLogService              │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - db: Session                       │          │ - db: Session                       │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + reconcile(table_id): Reconciliation          │ + log(action, entity, data): AuditLog
│ + compare_forms(forms): Comparison  │          │ + get_by_form(form_id): List        │
│ + select_winner(table_id, form_id)  │          │ + get_by_user(user_id): List        │
│ + finalize(table_id): None          │          │ + get_by_date_range(start, end): List
│ + dispute(table_id, reason): None   │          │ + export(filters): bytes            │
│ - _calculate_confidence(forms): float          │ # All entries are IMMUTABLE         │
└─────────────────────────────────────┘          └─────────────────────────────────────┘

┌─────────────────────────────────────┐
│      IngestionPipeline              │
├─────────────────────────────────────┤
│ - ocr_service: E14OCRService        │
│ - validation_svc: ValidationService │
│ - queue: Redis                      │
├─────────────────────────────────────┤
│ + ingest(file, metadata): str       │
│ + batch_ingest(files): List[str]    │
│ + get_status(job_id): JobStatus     │
│ + retry_failed(job_id): str         │
│ - _enqueue(job): None               │
│ - _process_job(job): Result         │
└─────────────────────────────────────┘
```

---

## 4. Dashboard Service - Diagrama de Clases

### 4.1 Modelos

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         DASHBOARD SERVICE - MODELS                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│           Analysis                  │          │           Tweet                     │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + id: UUID                          │          │ + id: UUID                          │
│ + user_id: UUID                     │          │ + analysis_id: UUID                 │
│ + candidate: str                    │          │ + tweet_id: str                     │
│ + location: str                     │          │ + text: str                         │
│ + topic_pnd: str                    │ 1      * │ + author: str                       │
│ + summary: str                      │◆────────>│ + author_followers: int             │
│ + strategy: str                     │          │ + retweets: int                     │
│ + speech: str                       │          │ + likes: int                        │
│ + charts_data: dict                 │          │ + sentiment: Sentiment              │
│ + metrics: dict                     │          │ + sentiment_score: Decimal          │
│ + tweet_count: int                  │          │ + topic_pnd: str                    │
│ + sentiment_distribution: dict      │          │ + tweet_date: datetime              │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + get_tweets(): List[Tweet]         │          │ + is_positive(): bool               │
│ + get_charts(): dict                │          │ + is_negative(): bool               │
│ + export_pdf(): bytes               │          │ + get_engagement(): int             │
└─────────────────────────────────────┘          └─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│         ChatSession                 │          │         ChatMessage                 │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + id: UUID                          │          │ + id: UUID                          │
│ + user_id: UUID                     │ 1      * │ + session_id: UUID                  │
│ + title: str                        │◆────────>│ + role: MessageRole                 │
│ + created_at: datetime              │          │ + content: str                      │
│ + updated_at: datetime              │          │ + tokens_used: int                  │
├─────────────────────────────────────┤          │ + model: str                        │
│ + get_messages(): List[ChatMessage] │          ├─────────────────────────────────────┤
│ + add_message(role, content): None  │          │ + is_user(): bool                   │
│ + get_context(): str                │          │ + is_assistant(): bool              │
└─────────────────────────────────────┘          └─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│          Forecast                   │          │        TrendingTopic                │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + id: UUID                          │          │ + id: UUID                          │
│ + user_id: UUID                     │          │ + name: str                         │
│ + candidate: str                    │          │ + tweet_volume: int                 │
│ + forecast_date: date               │          │ + location: str                     │
│ + icce: Decimal                     │          │ + rank: int                         │
│ + isn: Decimal                      │          │ + fetched_at: datetime              │
│ + icr: Decimal                      │          │ + expires_at: datetime              │
│ + momentum: Decimal                 │          ├─────────────────────────────────────┤
│ + sve: Decimal                      │          │ + is_expired(): bool                │
│ + ivn: Decimal                      │          └─────────────────────────────────────┘
│ + predictions: List[dict]           │
│ + confidence: Decimal               │          ┌─────────────────────────────────────┐
├─────────────────────────────────────┤          │        RAGDocument                  │
│ + get_trend(): str                  │          ├─────────────────────────────────────┤
│ + predict_winner(): bool            │          │ + id: UUID                          │
└─────────────────────────────────────┘          │ + content: str                      │
                                                 │ + source: str                       │
┌─────────────────────────────────────┐          │ + source_id: str                    │
│        CampaignAgent                │          │ + metadata: dict                    │
├─────────────────────────────────────┤          │ + embedding_id: str                 │
│ + id: UUID                          │          ├─────────────────────────────────────┤
│ + user_id: UUID                     │          │ + get_embedding(): List[float]      │
│ + candidate: str                    │          └─────────────────────────────────────┘
│ + analysis_type: str                │
│ + recommendations: List[dict]       │
│ + winning_strategies: List[dict]    │
├─────────────────────────────────────┤
│ + get_top_recommendations(): List   │
│ + export(): dict                    │
└─────────────────────────────────────┘
```

### 4.2 Services

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD SERVICE - SERVICES                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│         <<interface>>               │
│       ISentimentAnalyzer            │
├─────────────────────────────────────┤
│ + analyze(text): SentimentResult    │
│ + batch_analyze(texts): List        │
└─────────────────┬───────────────────┘
                  │
                  │ implements
                  ▼
┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│     BETOSentimentAnalyzer           │          │       SentimentService              │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - model: AutoModel                  │          │ - analyzer: ISentimentAnalyzer      │
│ - tokenizer: AutoTokenizer          │◄─────────│ - cache: Redis                      │
│ - device: str                       │          │ - cache_ttl: int = 86400            │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + analyze(text): SentimentResult    │          │ + analyze_tweets(tweets): Result    │
│ + batch_analyze(texts): List        │          │ + get_distribution(): dict          │
│ - _preprocess(text): str            │          │ + calculate_isn(): float            │
│ - _predict(tokens): Tensor          │          │ - _cache_key(text): str             │
│ - _to_sentiment(logits): Sentiment  │          └─────────────────────────────────────┘
└─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│         TwitterService              │          │       TrendingService               │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - client: tweepy.Client             │          │ - twitter_service: TwitterService   │
│ - bearer_token: str                 │◄─────────│ - cache: Redis                      │
│ - cache: Redis                      │          │ - cache_ttl: int = 21600            │
│ - daily_limit: int = 3              │          ├─────────────────────────────────────┤
├─────────────────────────────────────┤          │ + get_trending(location): List      │
│ + search_tweets(query, max): List   │          │ + detect_topics(tweets): List       │
│ + get_trending(woeid): List         │          │ + rank_by_relevance(topics): List   │
│ + get_user(username): User          │          └─────────────────────────────────────┘
│ - _check_rate_limit(): bool         │
│ - _cache_results(key, data): None   │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         <<interface>>               │
│          ILLMProvider               │
├─────────────────────────────────────┤
│ + generate(prompt): str             │
│ + chat(messages): str               │
│ + embed(text): List[float]          │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │ implements        │ implements
        ▼                   ▼
┌───────────────────┐ ┌───────────────────┐       ┌─────────────────────────────────────┐
│ OpenAIAdapter     │ │  ClaudeAdapter    │       │         OpenAIService               │
├───────────────────┤ ├───────────────────┤       ├─────────────────────────────────────┤
│ - client: OpenAI  │ │ - client:Anthropic│       │ - provider: ILLMProvider            │
│ - model: str      │ │ - model: str      │       │ - cache: Redis                      │
├───────────────────┤ ├───────────────────┤       │ - cache_ttl: int = 43200            │
│ + generate(): str │ │ + generate(): str │       ├─────────────────────────────────────┤
│ + chat(): str     │ │ + chat(): str     │◄──────│ + generate_summary(data): str       │
│ + embed(): List   │ │ + embed(): List   │       │ + generate_strategy(analysis): str  │
└───────────────────┘ └───────────────────┘       │ + generate_speech(context): str     │
                                                  │ + chat_completion(messages): str    │
                                                  │ - _build_prompt(template, data): str│
                                                  └─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│           RAGService                │          │       ForecastService               │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - vector_store: ChromaDB            │          │ - db: Session                       │
│ - embeddings: OpenAIEmbeddings      │          │ - forecast_days: int = 14           │
│ - llm: ILLMProvider                 │          ├─────────────────────────────────────┤
│ - collection_name: str              │          │ + predict(candidate): Forecast      │
├─────────────────────────────────────┤          │ + calculate_icce(data): float       │
│ + index_documents(docs): None       │          │ + calculate_isn(data): float        │
│ + search(query, k): List[Document]  │          │ + calculate_icr(data): float        │
│ + chat(query, history): str         │          │ + calculate_momentum(data): float   │
│ - _embed_text(text): List[float]    │          │ + calculate_sve(data): float        │
│ - _build_context(docs): str         │          │ - _holt_winters(series): Series     │
│ - _generate_response(ctx, q): str   │          │ - _trend_analysis(data): dict       │
└─────────────────────────────────────┘          └─────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│     TopicClassifierService          │          │      CampaignAgentService           │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ - pnd_categories: Dict[str, List]   │          │ - sentiment_svc: SentimentService   │
│ - embeddings_model: str             │          │ - openai_svc: OpenAIService         │
├─────────────────────────────────────┤          │ - forecast_svc: ForecastService     │
│ + classify(text): str               │          ├─────────────────────────────────────┤
│ + batch_classify(texts): List[str]  │          │ + analyze(candidate): CampaignAgent │
│ + get_pnd_distribution(tweets): dict│          │ + get_recommendations(): List       │
│ - _match_keywords(text, cat): float │          │ + get_winning_strategies(): List    │
│ - _semantic_similarity(t, c): float │          │ + optimize_message(msg): str        │
└─────────────────────────────────────┘          └─────────────────────────────────────┘
```

---

## 5. Clases Utilitarias Compartidas

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SHARED UTILITIES                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│           Config                    │          │        DatabaseService              │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + SECRET_KEY: str                   │          │ - engine: Engine                    │
│ + JWT_SECRET: str                   │          │ - session_factory: sessionmaker     │
│ + DATABASE_URL: str                 │          ├─────────────────────────────────────┤
│ + REDIS_URL: str                    │          │ + get_session(): Session            │
│ + OPENAI_API_KEY: str               │          │ + execute(query): Result            │
│ + ANTHROPIC_API_KEY: str            │          │ + commit(): None                    │
│ + TWITTER_BEARER_TOKEN: str         │          │ + rollback(): None                  │
│ + CACHE_TTL_*: int                  │          └─────────────────────────────────────┘
├─────────────────────────────────────┤
│ + load_from_env(): Config           │          ┌─────────────────────────────────────┐
│ + validate(): bool                  │          │         CacheService                │
└─────────────────────────────────────┘          ├─────────────────────────────────────┤
                                                 │ - redis: Redis                      │
┌─────────────────────────────────────┐          │ - default_ttl: int                  │
│         RateLimiter                 │          ├─────────────────────────────────────┤
├─────────────────────────────────────┤          │ + get(key): Any                     │
│ - redis: Redis                      │          │ + set(key, value, ttl): None        │
│ - limits: Dict[str, int]            │          │ + delete(key): None                 │
├─────────────────────────────────────┤          │ + exists(key): bool                 │
│ + check(key, limit): bool           │          │ + increment(key): int               │
│ + increment(key): int               │          │ + expire(key, ttl): None            │
│ + reset(key): None                  │          └─────────────────────────────────────┘
│ + get_remaining(key): int           │
└─────────────────────────────────────┘          ┌─────────────────────────────────────┐
                                                 │        CircuitBreaker               │
┌─────────────────────────────────────┐          ├─────────────────────────────────────┤
│         HTTPClient                  │          │ - failure_threshold: int = 5        │
├─────────────────────────────────────┤          │ - recovery_timeout: int = 30        │
│ - session: aiohttp.ClientSession    │          │ - state: CircuitState               │
│ - timeout: int                      │          │ - failure_count: int                │
│ - circuit_breaker: CircuitBreaker   │          │ - last_failure: datetime            │
├─────────────────────────────────────┤          ├─────────────────────────────────────┤
│ + get(url, headers): Response       │          │ + call(func): Any                   │
│ + post(url, data, headers): Response│          │ + is_open(): bool                   │
│ + put(url, data, headers): Response │          │ + record_failure(): None            │
│ + delete(url, headers): Response    │          │ + record_success(): None            │
│ - _handle_error(error): None        │          │ + reset(): None                     │
└─────────────────────────────────────┘          └─────────────────────────────────────┘
```

---

## 6. Enumeraciones Completas

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                ENUMERATIONS                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  <<enumeration>>  │  │  <<enumeration>>  │  │  <<enumeration>>  │  │  <<enumeration>>  │
│    UserRole       │  │   LeadStatus      │  │   ElectionType    │  │  ElectionStatus   │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ ADMIN             │  │ NEW               │  │ PRESIDENTIAL      │  │ SCHEDULED         │
│ ANALYST           │  │ CONTACTED         │  │ LEGISLATIVE       │  │ IN_PROGRESS       │
│ OBSERVER          │  │ QUALIFIED         │  │ REGIONAL          │  │ COMPLETED         │
│ VIEWER            │  │ CONVERTED         │  │ LOCAL             │  │ CANCELLED         │
└───────────────────┘  │ LOST              │  │ REFERENDUM        │  └───────────────────┘
                       └───────────────────┘  └───────────────────┘

┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  <<enumeration>>  │  │  <<enumeration>>  │  │  <<enumeration>>  │  │  <<enumeration>>  │
│   ContestType     │  │    FormType       │  │   SourceType      │  │ProcessingStatus   │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ PRESIDENT         │  │ E14               │  │ WITNESS           │  │ PENDING           │
│ SENATE            │  │ E24               │  │ OFFICIAL          │  │ PROCESSING        │
│ HOUSE             │  │ E26               │  │ BOLETIN           │  │ COMPLETED         │
│ GOVERNOR          │  │ BOLETIN           │  │ SCRAPER           │  │ FAILED            │
│ MAYOR             │  │ OTHER             │  └───────────────────┘  │ NEEDS_REVIEW      │
│ COUNCIL           │  └───────────────────┘                         │ VALIDATED         │
└───────────────────┘                                                └───────────────────┘

┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  <<enumeration>>  │  │  <<enumeration>>  │  │  <<enumeration>>  │  │  <<enumeration>>  │
│  AlertSeverity    │  │   AlertStatus     │  │ReconciliationStatus│ │   AuditAction     │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ INFO              │  │ OPEN              │  │ PROVISIONAL       │  │ CREATE            │
│ LOW               │  │ ACKNOWLEDGED      │  │ FINAL             │  │ UPDATE            │
│ MEDIUM            │  │ INVESTIGATING     │  │ DISPUTED          │  │ DELETE            │
│ HIGH              │  │ RESOLVED          │  └───────────────────┘  │ REVIEW_APPROVED   │
│ CRITICAL          │  │ FALSE_POSITIVE    │                         │ REVIEW_REJECTED   │
└───────────────────┘  └───────────────────┘                         │ RECONCILE         │
                                                                     │ ALERT_CREATED     │
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │ ALERT_RESOLVED    │
│  <<enumeration>>  │  │  <<enumeration>>  │  │  <<enumeration>>  │  └───────────────────┘
│   RiskLevel       │  │   Sentiment       │  │  MessageRole      │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ LOW               │  │ POSITIVE          │  │ USER              │
│ MEDIUM            │  │ NEGATIVE          │  │ ASSISTANT         │
│ HIGH              │  │ NEUTRAL           │  │ SYSTEM            │
│ EXTREME           │  └───────────────────┘  └───────────────────┘
└───────────────────┘

┌───────────────────┐
│  <<enumeration>>  │
│  CircuitState     │
├───────────────────┤
│ CLOSED            │
│ OPEN              │
│ HALF_OPEN         │
└───────────────────┘
```

---

## 7. Diagrama de Relaciones entre Clases

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           RELACIONES ENTRE CLASES                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

NOTACIÓN:
─────────────────────────────────────────────────────────────────────────────────────
    ──────>     Asociación direccional
    ◆─────>     Composición (el contenedor es dueño del contenido)
    ◇─────>     Agregación (relación débil)
    - - - ->    Dependencia
    ─────|>     Herencia (generalización)
    - - -|>     Implementación de interfaz
─────────────────────────────────────────────────────────────────────────────────────


                                    CORE SERVICE
═══════════════════════════════════════════════════════════════════════════════════════

                              BaseModel
                                  △
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                  User        Session         Lead
                    │             │
                    │ 1           │ *
                    ◆─────────────┘
                    │
                    │ 1
                    ◆
                    │
              UserSettings


                              IAuthService
                                  △
                                  ┊ implements
                                  │
                             AuthService ◆────────> TokenService
                                  │
                                  ◇────────> UserService


                                    E-14 SERVICE
═══════════════════════════════════════════════════════════════════════════════════════

    Election ◆──────> Contest ◆──────> Candidate <──────◇ Party
                          │
                          │
    Department ◆──> Municipality ◆──> PollingStation ◆──> PollingTable
                                                               │
                                                               │ 1
                                                               ◆
                                                               │ *
                                                         FormInstance
                                                               │
                                  ┌─────────────┬──────────────┼──────────────┐
                                  │             │              │              │
                                  ◆             ◆              ◆              ◆
                                  │ *           │ *            │ *            │ *
                              OCRField     VoteTally    ValidationResult  Discrepancy
                                                                              │
                                                                              │ 1
                                                                              ◆
                                                                              │ *
                                                                            Alert


    IOCRProvider                                ValidationService
        △                                              │
        ┊ implements                                   ◆────────> AlertService
        │                                              │
  ClaudeOCRAdapter <──────◇ E14OCRService              ◇────────> AuditLogService


                                 DASHBOARD SERVICE
═══════════════════════════════════════════════════════════════════════════════════════

    Analysis ◆──────> Tweet
        │
        │
    ChatSession ◆──────> ChatMessage


    ISentimentAnalyzer                    ILLMProvider
          △                                    △
          ┊ implements                         ┊ implements
          │                              ┌─────┴─────┐
  BETOSentimentAnalyzer            OpenAIAdapter  ClaudeAdapter
          △                              │
          │                              │
    SentimentService              OpenAIService
          │                              │
          ◇                              │
          │                              │
    TwitterService <────────────────┬────┴───────────┬──────────────> RAGService
                                    │                │
                              ForecastService   CampaignAgentService
                                    │                │
                                    ◇────────────────◇
                                    │
                            TopicClassifierService
```

---

## 8. Resumen de Clases por Paquete

| Paquete | Tipo | Cantidad | Clases Principales |
|---------|------|----------|-------------------|
| **core_service.models** | Entity | 4 | User, Session, Lead, UserSettings |
| **core_service.services** | Service | 4 | AuthService, TokenService, UserService, LeadService |
| **core_service.schemas** | DTO | 5 | LoginRequest, LoginResponse, UserResponse, etc. |
| **e14_service.models** | Entity | 15 | Election, Contest, Candidate, FormInstance, Alert, etc. |
| **e14_service.services** | Service | 7 | E14OCRService, ValidationService, AlertService, etc. |
| **dashboard_service.models** | Entity | 7 | Analysis, Tweet, ChatSession, Forecast, etc. |
| **dashboard_service.services** | Service | 8 | SentimentService, TwitterService, RAGService, etc. |
| **shared.utils** | Utility | 6 | Config, DatabaseService, CacheService, RateLimiter, etc. |
| **Enums** | Enum | 16 | UserRole, FormType, AlertSeverity, Sentiment, etc. |
| **Interfaces** | Interface | 4 | IAuthService, IOCRProvider, ISentimentAnalyzer, ILLMProvider |

**Total: ~70 clases**

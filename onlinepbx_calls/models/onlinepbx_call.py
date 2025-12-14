from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OnlinePBXCall(models.Model):
    _name = 'onlinepbx.call'
    _description = 'OnlinePBX Call'
    _order = 'start_time desc, id desc'

    name = fields.Char(string="Call ID", required=True)
    start_time = fields.Datetime(string="Date Time")
    direction = fields.Selection(
        [
            ('in', 'Incoming'),
            ('out', 'Outgoing'),
            ('local', 'Internal'),
        ],
        string="Type",
        default='in',
        required=True,
    )
    state = fields.Selection(
        [
            ('answered', 'Answered'),
            ('not_answered', 'Not answered'),
            ('missed', 'Missed'),
        ],
        string="Status",
        default='not_answered',
        required=True,
    )

    from_number = fields.Char(string="From")
    to_number = fields.Char(string="To")
    external_number = fields.Char(string="External Number")

    duration_seconds = fields.Integer(string="Talk Time (sec)")
    duration_display = fields.Char(
        string="Talk Time",
        compute="_compute_duration_display",
        store=False,
    )

    has_recording = fields.Boolean(string="Has Recording")
    recording_url = fields.Char(string="Play URL (PBX)")
    download_url = fields.Char(string="Download URL (PBX)")

    # internal player/proxy url (for embedded <audio>)
    player_url = fields.Char(
        string="Play URL",
        compute="_compute_player_url",
        store=False,
    )

    # html snippet with <audio> tag
    audio_embed = fields.Html(
        string="Player",
        compute="_compute_audio_embed",
        sanitize=False,
        readonly=True,
    )

    # raw webhook body for debugging
    raw_payload = fields.Text(string="Raw Payload", readonly=True)

    # -------- SCORING --------
    rating_ids = fields.One2many(
        'onlinepbx.call.rating',
        'call_id',
        string="Category Ratings",
    )

    # keep as Selection (legacy, to satisfy old DB schema)
    overall_score = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string="Overall Score",
        compute="_compute_overall_score",
        store=True,
    )

    # NEW FIELD – this is what you actually use now
    total_score = fields.Integer(
        string="Overall Score",
        help="Sum of all category scores.",
    )

    objection_ids = fields.Many2many(
        'onlinepbx.objection',
        'onlinepbx_call_objection_rel',
        'call_id',
        'objection_id',
        string="Objections",
    )

    
    employee_extension = fields.Char(
        string="Employee Extension",
        help="Extension received from PBX that we use to match an employee.",
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        help="Employee matched by PBX extension.",
        index=True,
    )
    
    numbers_all = fields.Char(
        string="All Numbers",
        compute="_compute_numbers_all",
        store=True,
        index=True,
        help="Concatenation of From / To / External numbers for easy searching.",
    )
    
    call_count = fields.Integer(
        string="Calls",
        default=1,
        help="Technical field for graphs (1 row = 1 call).",
    )

    # ----------------- COMPUTES ------------------

    @api.depends('from_number', 'to_number', 'external_number')
    def _compute_numbers_all(self):
        for rec in self:
            parts = [p for p in [rec.from_number, rec.to_number, rec.external_number] if p]
            rec.numbers_all = " ".join(parts)

    
    # ---------------------------------------------------
    # existing code ...
    # ---------------------------------------------------

    @api.depends('state', 'objection_ids', 'has_recording')
    def _compute_kpi_flags(self):
        for rec in self:
            rec.answered_count = 1 if rec.state == 'answered' else 0
            rec.missed_count = 1 if rec.state == 'missed' else 0
            rec.not_answered_count = 1 if rec.state == 'not_answered' else 0
            rec.problem_count = 1 if rec.objection_ids else 0
            rec.recording_count = 1 if rec.has_recording else 0
    
    
    
    # ========= KPI / MEASURE FIELDS FOR GRAPHS =========
    answered_count = fields.Integer(
        string="Answered Calls",
        compute="_compute_kpi_flags",
        store=True,
    )
    missed_count = fields.Integer(
        string="Missed Calls",
        compute="_compute_kpi_flags",
        store=True,
    )
    not_answered_count = fields.Integer(
        string="Not Answered Calls",
        compute="_compute_kpi_flags",
        store=True,
    )
    problem_count = fields.Integer(
        string="Problem Calls",
        compute="_compute_kpi_flags",
        store=True,
        help="1 if the call has at least one objection.",
    )
    recording_count = fields.Integer(
        string="Recorded Calls",
        compute="_compute_kpi_flags",
        store=True,
        help="1 if the call has a recording.",
    )
    
    
    # ----------------- OVERRIDES -----------------

    @api.depends('rating_ids.points')
    def _compute_overall_score(self):
        """Sum of all category points."""
        for rec in self:
            total = sum((line.points or 0) for line in rec.rating_ids)
            rec.total_score = total

            # keep legacy selection field in a safe value (or False)
            # here I just clear it – it's not used anywhere
            rec.overall_score = False


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_default_ratings()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._ensure_default_ratings()
        return res

    # ----------------- HELPERS -------------------

    def _ensure_default_ratings(self):
        """
        Make sure each call has one rating line
        for every active score category.
        """
        categories = self.env['onlinepbx.score.category'].search([('active', '=', True)])
        for rec in self:
            if not categories:
                continue
            existing_cats = rec.rating_ids.mapped('category_id')
            missing = categories - existing_cats
            for cat in missing:
                self.env['onlinepbx.call.rating'].create({
                    'call_id': rec.id,
                    'category_id': cat.id,
                })

    # ----------------- COMPUTES ------------------

    @api.depends('duration_seconds')
    def _compute_duration_display(self):
        for rec in self:
            s = rec.duration_seconds or 0
            minutes = s // 60
            seconds = s % 60
            rec.duration_display = f"{minutes}m {seconds:02d}s"

    def _compute_player_url(self):
        for rec in self:
            if rec.id and (rec.download_url or rec.recording_url):
                rec.player_url = f"/onlinepbx/stream/{rec.id}"
            else:
                rec.player_url = False

    @api.depends('player_url', 'has_recording')
    def _compute_audio_embed(self):
        for rec in self:
            if rec.has_recording and rec.player_url:
                rec.audio_embed = f"""
                    <audio controls style="width:350px; height:35px;">
                        <source src="{rec.player_url}" type="audio/mpeg"/>
                        Your browser does not support the audio element.
                    </audio>
                """
            else:
                rec.audio_embed = ""


class OnlinePBXScoreCategory(models.Model):
    _name = 'onlinepbx.score.category'
    _description = 'OnlinePBX Score Category'

    name = fields.Char(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)

    # per-category max points
    max_points = fields.Integer(
        string="Max Points",
        default=5,
        help="Maximum points the operator can give for this category.",
    )


class OnlinePBXCallRating(models.Model):
    _name = 'onlinepbx.call.rating'
    _description = 'OnlinePBX Call Rating by Category'

    call_id = fields.Many2one('onlinepbx.call', required=True, ondelete='cascade')
    category_id = fields.Many2one('onlinepbx.score.category', required=True)

    # OLD FIELD – keep selection, don't use in UI
    score = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string="Legacy Score (1-5)",
        required=False,
    )

    # NEW FIELD – real numeric score we work with
    points = fields.Integer(
        string="Score",
        required=False,
        help="Score for this category, cannot exceed the category's Max.",
    )

    # readonly column showing the category's max_points
    max_points = fields.Integer(
        string="Max",
        related='category_id.max_points',
        store=False,
        readonly=True,
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        related='call_id.employee_id',
        store=True,
        string="Employee",
    )

    note = fields.Char(string="Comment")

    @api.constrains('points', 'max_points')
    def _check_points_not_above_max(self):
        for rec in self:
            if rec.points is None:
                continue
            if rec.points < 0:
                raise ValidationError(_("Score cannot be negative."))
            if rec.max_points and rec.points > rec.max_points:
                raise ValidationError(
                    _("Score for '%s' cannot be greater than %d.")
                    % (rec.category_id.name, rec.max_points)
                )


class OnlinePBXObjection(models.Model):
    _name = 'onlinepbx.objection'
    _description = "OnlinePBX Objection / Reason"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

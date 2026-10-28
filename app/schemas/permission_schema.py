from marshmallow import Schema, fields


class PlainPermissionSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True, load_default=None)


class UpdatePermissionRoleSchema(Schema):
    data_update = fields.Dict(required=True)

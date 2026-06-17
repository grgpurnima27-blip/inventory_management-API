def add_tenant_auth_to_schema(result, generator, request, public):
    """
    Postprocessing hook — injects X-Tenant-Slug as a named security scheme
    so it appears in Swagger UI's Authorize dialog alongside the JWT field.

    After the user logs in, the response includes  tenant.slug  — they paste
    that value here once and every request automatically sends the header.
    """
    components = result.setdefault('components', {})
    schemes    = components.setdefault('securitySchemes', {})

    schemes['tenantAuth'] = {
        'type':        'apiKey',
        'in':          'header',
        'name':        'X-Tenant-Slug',
        'description': (
            'Your store slug (e.g. **techmart**). '
            'You get this from the login response under `tenant.slug`. '
            'Required for all store endpoints (products, warehouses, inventory, orders, etc.).'
        ),
    }

    # Add to global security so every endpoint shows both locks in Swagger UI
    security = result.setdefault('security', [])
    if {'tenantAuth': []} not in security:
        security.append({'tenantAuth': []})

    return result

from discord import *

# ID de los roles que pueden ejecutar los comandos (NO HAY DISTINCION ENTRE COMANDOS, LOS ROLES QUE HAYAN AQUI PUEDEN EJECUTAR TODO)
ROLES_PERMITIDOS:list[int] = [1335571420570194043, 1498376308806385754]


"""
Verifica si un usuario es miembro de uno de los roles en la lista permitida, sino, devuelve false
"""
def usuario_puede_ejecutar_comando(contexto):
    usuario_ejecutor:Member = contexto.author
    roles:list[Role] = usuario_ejecutor.roles
    
    for rol in roles:
        if(rol.id in ROLES_PERMITIDOS): return True
        else: continue
        
    return False
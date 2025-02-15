(* Returns possibly the inferred type of the expression, as well as an ident
 * option that can then be used to query LSP to get the type of the ident. *)
val type_of_expr :
  Lang.t ->
  AST_generic.expr ->
  AST_generic.name Type.t * AST_generic.ident option

val resolved_type_of_id_info :
  Lang.t -> AST_generic.id_info -> AST_generic.name Type.t

val check_program : Lang.t -> AST_generic.program -> unit

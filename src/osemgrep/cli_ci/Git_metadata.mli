(** Gather metadata only from local filesystem. We expect, at least, a Git
    repository. *)

type env = {
  _SEMGREP_REPO_NAME : string option;
  _SEMGREP_REPO_URL : Uri.t option;
  _SEMGREP_COMMIT : Digestif.SHA1.t option;
  _SEMGREP_JOB_URL : Uri.t option;
  _SEMGREP_PR_ID : string option;
  _SEMGREP_PR_TITLE : string option;
  _SEMGREP_BRANCH : string option;
}

include Project_metadata.S with type extension = unit and type env := env

import torch


def append_bias_ones(tensor):
    """Appends vector of ones to last dimension of tensor.

    For examples, if the input is of shape [4, 6], then the outputs has shape
    [4, 7] where the slice [:, -1] is a tensor of all ones.
    """
    shape = list(tensor.shape[:-1]) + [1]
    return torch.cat([tensor, tensor.new_ones(shape)], dim=-1)


def get_cov(a, b=None, scale=None):
    """Computes the empirical second moment of a 2D tensor

    Reference:
      - https://github.com/tensorflow/kfac/blob/master/kfac/python/ops/fisher_factors.py#L220  # noqa: E501
      - https://arxiv.org/pdf/1602.01407.pdf#subsection.2.2

    Args:
      a (tensor): 2D tensor to compute second moment of using cov_a = a^T @ a.
      b (tensor, optional): optional tensor of equal shape to a such that
          cov_a = a^T @ b.
      scale (float, optional): optional tensor to divide cov_a by. Default is
          a.size(0).

    Returns:
      A square tensor representing the second moment of a.
    """
    if len(a.shape) != 2:
        raise ValueError(
            "Input tensor must have 2 dimensions. Got tensor with shape "
            f"{a.shape}",
        )
    if b is not None and a.shape != b.shape:
        raise ValueError(
            "Input tensors must have same shape. Got tensors of "
            "shape {} and {}.".format(a.shape, b.shape),
        )

    if scale is None:
        scale = a.size(0)

    if b is None:
        cov_a = a.t() @ (a / scale)
        # TODO(gpauloski): is this redundant?
        return (cov_a + cov_a.t()) / 2.0
    else:
        return a.t() @ (b / scale)


def get_elementwise_inverse(vector, damping=None):
    """Computes the reciprocal of each non-zero element of v"""
    if damping is not None:
        vector = vector + damping
    mask = vector != 0.0
    reciprocal = vector.clone()
    reciprocal[mask] = torch.reciprocal(reciprocal[mask])
    return reciprocal


def reshape_data(data_list, batch_first=True, collapse_dims=False):
    """Concat input/output data and clear buffers

    Args:
      data_list (list): list of tensors of equal, arbitrary shape where the
          batch_dim is either 0 or 1 depending on self.batch_first.
      batch_first (bool, optional): is batch dim first. (default: True)
      collapse_dim (bool, optional): if True, collapse all but the last dim
          together forming a 2D output tensor.

    Returns:
      Single tensor with all tensors from data_list concatenated across
      batch_dim. Guarenteed to be 2D if collapse_dims=True.
    """
    d = torch.cat(data_list, dim=int(not batch_first))
    if collapse_dims and len(d.shape) > 2:
        d = d.view(-1, d.shape[-1])
    return d


def update_running_avg(new, current, alpha=1.0):
    """Computes in-place running average

    current = alpha*current + (1-alpha)*new

    Args:
      new (tensor): tensor to add to current average
      current (tensor): tensor containing current average. Result will be
          saved in place to this tensor.
      alpha (float, optional): (default: 1.0)
    """
    if alpha != 1:
        current *= alpha / (1 - alpha)
        current += new
        current *= 1 - alpha

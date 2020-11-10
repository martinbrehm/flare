#ifndef SQUARED_EXPONENTIAL_H
#define SQUARED_EXPONENTIAL_H

#include "kernel.h"
#include <Eigen/Dense>
#include <vector>

class DescriptorValues;
class ClusterDescriptor;

class SquaredExponential : public CompactKernel {
public:
  double sigma, ls, sig2, ls2;

  SquaredExponential();

  SquaredExponential(double sigma, double ls);

  Eigen::MatrixXd envs_envs(const ClusterDescriptor &envs1,
                            const ClusterDescriptor &envs2);

  Eigen::MatrixXd envs_envs_grad(const ClusterDescriptor &envs1,
                                 const ClusterDescriptor &envs2,
                                 const Eigen::MatrixXd &Kuu);

  Eigen::MatrixXd envs_struc(const ClusterDescriptor &envs,
                             const DescriptorValues &struc);

  Eigen::VectorXd self_kernel_struc(DescriptorValues struc);

  Eigen::MatrixXd struc_struc(DescriptorValues struc1,
                              DescriptorValues struc2);

  void set_hyperparameters(Eigen::VectorXd new_hyps);
};

#endif

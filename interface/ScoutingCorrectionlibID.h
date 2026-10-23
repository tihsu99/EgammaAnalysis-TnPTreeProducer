#ifndef EgammaAnalysis_TnPTreeProducer_ScoutingCorrectionlibID_h
#define EgammaAnalysis_TnPTreeProducer_ScoutingCorrectionlibID_h

#include "correction.h"

#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

// Full raw-input ID evaluation shared by electron and photon selectors.
class ScoutingCorrectionlibID {
public:
  ScoutingCorrectionlibID(const std::string& filename, const std::string& workingPoint)
      : corrections_(correction::CorrectionSet::from_file(filename)), name_(workingPoint) {
    if (corrections_->compound().empty()) {
      simple_ = corrections_->at(name_);
    } else {
      compound_ = corrections_->compound().at(name_);
    }
    const auto& output = compound_ ? compound_->output() : simple_->output();
    if (output.name() != "pass" || output.type() != correction::Variable::VarType::real) {
      throw std::invalid_argument(name_ + " must be a full ID with a real 'pass' output");
    }
    const auto& inputs = compound_ ? compound_->inputs() : simple_->inputs();
    for (const auto& input : inputs) {
      if (input.type() != correction::Variable::VarType::real) {
        throw std::invalid_argument(name_ + " requires a non-real input: " + input.name());
      }
      inputs_.push_back(input.name());
    }
  }

  const std::vector<std::string>& inputs() const { return inputs_; }

  bool evaluate(const std::vector<double>& values) const {
    if (values.size() != inputs_.size()) {
      throw std::invalid_argument(name_ + " input count does not match its correctionlib signature");
    }
    std::vector<correction::Variable::Type> arguments;
    arguments.reserve(values.size());
    for (double value : values) {
      if (!std::isfinite(value)) {
        return false;
      }
      arguments.emplace_back(value);
    }
    const double result = compound_ ? compound_->evaluate(arguments) : simple_->evaluate(arguments);
    if (result != 0. && result != 1.) {
      throw std::runtime_error(name_ + " did not return a binary ID decision");
    }
    return result == 1.;
  }

private:
  std::unique_ptr<correction::CorrectionSet> corrections_;
  std::string name_;
  correction::Correction::Ref simple_;
  correction::CompoundCorrection::Ref compound_;
  std::vector<std::string> inputs_;
};

#endif

#include "EgammaAnalysis/TnPTreeProducer/interface/ScoutingCorrectionlibID.h"
#include "CommonTools/Utils/interface/StringCutObjectSelector.h"
#include "CommonTools/Utils/interface/StringObjectFunction.h"
#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/RefVector.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"
#include "DataFormats/Scouting/interface/Run3ScoutingPhoton.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;
using LeafCandidateRefVector = edm::RefVector<LeafCandidateCollection>;

template <typename Particle>
class ScoutingCorrectionlibRefSelector : public edm::one::EDProducer<> {
public:
  explicit ScoutingCorrectionlibRefSelector(const edm::ParameterSet& config)
      : inputToken_(consumes<LeafCandidateRefVector>(config.getParameter<edm::InputTag>("input"))),
        srcToken_(consumes<std::vector<Particle>>(config.getParameter<edm::InputTag>("src"))),
        candidatesToken_(consumes<LeafCandidateCollection>(config.getParameter<edm::InputTag>("candidates"))),
        id_(config.getParameter<std::string>("correctionFile"), config.getParameter<std::string>("workingPoint")),
        cut_(config.getParameter<std::string>("cut")) {
    const auto mappings = config.getParameter<std::vector<edm::ParameterSet>>("variables");
    if (mappings.size() != id_.inputs().size()) {
      throw cms::Exception("Configuration") << "Correctionlib input mapping count does not match the ID";
    }
    for (size_t i = 0; i < mappings.size(); ++i) {
      const auto& mapping = mappings[i];
      if (mapping.getParameter<std::string>("name") != id_.inputs()[i]) {
        throw cms::Exception("Configuration") << "Correctionlib input order mismatch at " << id_.inputs()[i];
      }
      const bool expression = mapping.existsAs<std::string>("expression");
      const bool eventValue = mapping.existsAs<edm::InputTag>("src");
      if (expression == eventValue) {
        throw cms::Exception("Configuration") << "Map " << id_.inputs()[i] << " to exactly one expression or event product";
      }
      ValueInput input;
      if (expression) {
        input.function = std::make_unique<StringObjectFunction<Particle>>(mapping.getParameter<std::string>("expression"));
      } else {
        input.token = consumes<double>(mapping.getParameter<edm::InputTag>("src"));
      }
      variables_.push_back(std::move(input));
    }
    produces<LeafCandidateRefVector>();
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<LeafCandidateRefVector> input;
    edm::Handle<std::vector<Particle>> source;
    edm::Handle<LeafCandidateCollection> candidates;
    event.getByToken(inputToken_, input);
    event.getByToken(srcToken_, source);
    event.getByToken(candidatesToken_, candidates);
    if (!input.isValid() || !source.isValid() || !candidates.isValid()) {
      throw cms::Exception("ProductNotFound") << "Missing scouting correctionlib selector input";
    }
    // The scouting candidate converters preserve the original collection order.
    if (source->size() != candidates->size()) {
      throw cms::Exception("InvalidReference") << "Scouting raw and candidate collection sizes differ";
    }
    std::vector<double> values(variables_.size());
    for (size_t i = 0; i < variables_.size(); ++i) {
      if (!variables_[i].function) {
        edm::Handle<double> value;
        event.getByToken(variables_[i].token, value);
        if (!value.isValid()) {
          throw cms::Exception("ProductNotFound") << "Missing correctionlib event input " << id_.inputs()[i];
        }
        values[i] = *value;
      }
    }
    auto output = std::make_unique<LeafCandidateRefVector>();
    for (const auto& ref : *input) {
      if (ref.isNull() || ref.id() != candidates.id() || ref.key() >= source->size()) {
        throw cms::Exception("InvalidReference") << "Scouting correctionlib selector received an incompatible reference";
      }
      if (!cut_(*ref)) {
        continue;
      }
      for (size_t i = 0; i < variables_.size(); ++i) {
        if (variables_[i].function) {
          values[i] = (*variables_[i].function)((*source)[ref.key()]);
        }
      }
      if (id_.evaluate(values)) {
        output->push_back(ref);
      }
    }
    event.put(std::move(output));
  }

private:
  struct ValueInput {
    std::unique_ptr<StringObjectFunction<Particle>> function;
    edm::EDGetTokenT<double> token;
  };
  edm::EDGetTokenT<LeafCandidateRefVector> inputToken_;
  edm::EDGetTokenT<std::vector<Particle>> srcToken_;
  edm::EDGetTokenT<LeafCandidateCollection> candidatesToken_;
  ScoutingCorrectionlibID id_;
  StringCutObjectSelector<reco::LeafCandidate> cut_;
  std::vector<ValueInput> variables_;
};

using ScoutingElectronCorrectionlibRefSelector = ScoutingCorrectionlibRefSelector<Run3ScoutingElectron>;
using ScoutingPhotonCorrectionlibRefSelector = ScoutingCorrectionlibRefSelector<Run3ScoutingPhoton>;
DEFINE_FWK_MODULE(ScoutingElectronCorrectionlibRefSelector);
DEFINE_FWK_MODULE(ScoutingPhotonCorrectionlibRefSelector);

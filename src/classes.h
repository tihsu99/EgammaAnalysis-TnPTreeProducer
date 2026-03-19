#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/Ref.h"
#include "DataFormats/Common/interface/RefProd.h"
#include "DataFormats/Common/interface/RefVector.h"
#include "DataFormats/Common/interface/Wrapper.h"

#include <vector>

namespace {
  struct dictionary {
    edm::Ref<std::vector<reco::LeafCandidate>> leafCandidateRef;
    edm::RefProd<std::vector<reco::LeafCandidate>> leafCandidateRefProd;
    edm::RefVector<std::vector<reco::LeafCandidate>> leafCandidateRefVector;

    edm::Wrapper<edm::Ref<std::vector<reco::LeafCandidate>>> leafCandidateRefWrapper;
    edm::Wrapper<edm::RefProd<std::vector<reco::LeafCandidate>>> leafCandidateRefProdWrapper;
    edm::Wrapper<edm::RefVector<std::vector<reco::LeafCandidate>>> leafCandidateRefVectorWrapper;
  };
}

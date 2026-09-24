import pytest

solders = pytest.importorskip("solders")

from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0, to_bytes_versioned
from solders.null_signer import NullSigner
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

from jev_trader.swap import sign_versioned_for_taker


def _two_signer_message():
    payer = Keypair()
    taker = Keypair()
    program = Pubkey.new_unique()
    instruction = Instruction(
        program,
        bytes([1, 2, 3]),
        [
            AccountMeta(payer.pubkey(), True, True),
            AccountMeta(taker.pubkey(), True, True),
        ],
    )
    message = MessageV0.try_compile(payer.pubkey(), [instruction], [], Hash.default())
    return payer, taker, message


def test_gasless_keeps_default_payer_signature_and_signs_taker_slot():
    _payer, taker, message = _two_signer_message()
    unsigned = VersionedTransaction(
        message,
        [NullSigner(_payer.pubkey()), NullSigner(taker.pubkey())],
    )
    signed = VersionedTransaction.from_bytes(sign_versioned_for_taker(bytes(unsigned), taker))
    assert bytes(signed.signatures[0]) == bytes(Signature.default())
    assert bytes(signed.signatures[1]) == bytes(taker.sign_message(to_bytes_versioned(message)))
    assert bytes(signed.signatures[1]) != bytes(Signature.default())


def test_gasless_preserves_an_existing_payer_signature():
    payer, taker, message = _two_signer_message()
    payer_signature = payer.sign_message(to_bytes_versioned(message))
    partial = VersionedTransaction.populate(message, [payer_signature, Signature.default()])
    signed = VersionedTransaction.from_bytes(sign_versioned_for_taker(bytes(partial), taker))
    assert bytes(signed.signatures[0]) == bytes(payer_signature)
    assert bytes(signed.signatures[1]) == bytes(taker.sign_message(to_bytes_versioned(message)))


def test_single_signer_taker_signs_the_only_slot():
    taker = Keypair()
    program = Pubkey.new_unique()
    instruction = Instruction(program, bytes([1]), [AccountMeta(taker.pubkey(), True, True)])
    message = MessageV0.try_compile(taker.pubkey(), [instruction], [], Hash.default())
    unsigned = VersionedTransaction(message, [NullSigner(taker.pubkey())])
    signed = VersionedTransaction.from_bytes(sign_versioned_for_taker(bytes(unsigned), taker))
    assert len(signed.signatures) == 1
    assert bytes(signed.signatures[0]) == bytes(taker.sign_message(to_bytes_versioned(message)))

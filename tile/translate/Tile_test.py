"""
==========================================================================
Tile_test.py
==========================================================================
Test cases for Tile.

Author : Cheng Tan
  Date : Mar 2, 2019

"""

from pymtl3 import *
from pymtl3.stdlib.test              import TestSinkCL
from pymtl3.stdlib.test.test_srcs    import TestSrcRTL

from ..Tile                          import Tile
from ...lib.opt_type                 import *
from ...lib.messages                 import *
from ...fu.single.Alu                import Alu
from ...fu.single.Mul                import Mul
from ...fu.single.MemUnit            import MemUnit
from ...fu.triple.ThreeMulAluShifter import ThreeMulAluShifter
from ...fu.flexible.FlexibleFu       import FlexibleFu
from ...mem.ctrl.CtrlMem             import CtrlMem

from pymtl3.passes.backends.verilog import TranslationImportPass

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, DUT, FunctionUnit, FuList, DataType, CtrlType,
                 ctrl_mem_size, data_mem_size,
                 num_tile_inports, num_tile_outports,
                 src_data, src_opt, opt_waddr, sink_out ):

    s.num_tile_inports  = num_tile_inports
    s.num_tile_outports = num_tile_outports

    AddrType    = mk_bits( clog2( ctrl_mem_size ) )

    s.src_opt   = TestSrcRTL( CtrlType, src_opt )
    s.opt_waddr = TestSrcRTL( AddrType, opt_waddr )
    s.src_data  = [ TestSrcRTL( DataType, src_data[i]  )
                  for i in range( num_tile_inports  ) ]
    s.sink_out  = [ TestSinkCL( DataType, sink_out[i] )
                  for i in range( num_tile_outports ) ]

    s.dut = DUT( FunctionUnit, FuList, DataType, CtrlType,
                 ctrl_mem_size, data_mem_size, len(src_opt) )

    connect( s.src_opt.send,   s.dut.recv_wopt  )
    connect( s.opt_waddr.send, s.dut.recv_waddr )

    for i in range( num_tile_inports ):
      connect( s.src_data[i].send, s.dut.recv_data[i] )
    for i in range( num_tile_outports ):
      connect( s.dut.send_data[i],  s.sink_out[i].recv )

#    is_memory_unit = False
#    for i in range( s.dut.element.fu_list_size ):
#      if hasattr(s.dut.element.fu[i], "to_mem_raddr"):
#        is_memory_unit = True
#    if is_memory_unit:

#    for i in range( len( FuList ) ):
#      if FuList[i] == MemUnit:
    s.dut.to_mem_raddr.rdy   //= 0
    s.dut.from_mem_rdata.en  //= 0
    s.dut.from_mem_rdata.msg //= DataType( 0, 0 )
    s.dut.to_mem_waddr.rdy   //= 0
    s.dut.to_mem_wdata.rdy   //= 0

  def done( s ):
    done = True
    for i in range( s.num_tile_outports ):
      if not s.sink_out[i].done():# and not s.src_data[i].done():
        done = False
        break
    return done

  def line_trace( s ):
    return s.dut.line_trace()

def run_sim( test_harness, max_cycles=100 ):
  test_harness.elaborate()
  test_harness.dut.verilog_translate_import = True
  test_harness.dut.config_verilog_import = VerilatorImportConfigs(vl_Wno_list =         ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT', 'ALWCOMBORDER'])
  test_harness = TranslationImportPass()(test_harness)
  test_harness.apply( SimulationPass() )
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print()
  print( "{}:{}".format( ncycles, test_harness.line_trace() ))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.tick()
    ncycles += 1
    print( "{}:{}".format( ncycles, test_harness.line_trace() ))

  # Check timeout

  assert ncycles < max_cycles

  test_harness.tick()
  test_harness.tick()
  test_harness.tick()

def test_tile_alu():
  num_tile_inports  = 4
  num_tile_outports = 4
  num_xbar_inports  = 6
  num_xbar_outports = 8
  ctrl_mem_size     = 3
  data_mem_size     = 8
  RouteType    = mk_bits( clog2( num_xbar_inports + 1 ) )
  AddrType     = mk_bits( clog2( ctrl_mem_size ) )
  DUT          = Tile
  FunctionUnit = FlexibleFu
  FuList      = [Alu, MemUnit]
#  FuList      = [Alu, Mul]
  DataType     = mk_data( 32, 1 )
  CtrlType     = mk_ctrl( num_xbar_inports, num_xbar_outports )
  opt_waddr    = [ AddrType( 0 ), AddrType( 1 ), AddrType( 2 ) ]
  src_opt      = [ CtrlType( OPT_NAH, [
                   RouteType(4), RouteType(3), RouteType(2), RouteType(1),
                   RouteType(4), RouteType(3), RouteType(2), RouteType(1)] ),
                   CtrlType( OPT_ADD, [
                   RouteType(3), RouteType(3), RouteType(3), RouteType(5),
                   RouteType(4), RouteType(1), RouteType(1), RouteType(1)] ),
                   CtrlType( OPT_SUB, [
                   RouteType(5), RouteType(5), RouteType(2), RouteType(2),
                   RouteType(1), RouteType(1), RouteType(1), RouteType(1)] ) ]
  src_data     = [ [DataType(2, 1), DataType( 3, 1)],
                   [DataType(3, 1), DataType( 4, 1)],
                   [DataType(4, 1), DataType( 5, 1)],
                   [DataType(5, 1), DataType( 6, 1)] ]
  sink_out     = [ [DataType(5, 1), DataType( 5, 1), DataType( 3, 1)],
                   [DataType(4, 1), DataType( 5, 1), DataType( 3, 1)],
                   [DataType(3, 1), DataType( 5, 1)],
                   [DataType(2, 1), DataType( 9, 1)] ]
  th = TestHarness( DUT, FunctionUnit, FuList, DataType, CtrlType,
                    ctrl_mem_size, data_mem_size,
                    num_tile_inports, num_tile_outports,
                    src_data, src_opt, opt_waddr, sink_out )
  run_sim( th )
